#!/usr/bin/env python3
"""Construit news.json à partir de flux RSS publics. Bibliothèque standard uniquement."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("BMW Group PressClub France", "https://www.press.bmwgroup.com/france/rss/"),
    ("Automobile Propre", "https://www.automobile-propre.com/feed/"),
    ("L'Argus", "https://www.largus.fr/rss/actualites.xml"),
    ("Caradisiac", "https://www.caradisiac.com/rss/"),
    ("Ministère de l'Économie", "https://www.economie.gouv.fr/flux-rss"),
]

KEYWORDS = {
    "MINI et BMW": [
        "mini", "bmw", "bmw group", "cooper", "countryman", "aceman",
        "john cooper works", "electric", "électrique", "nouveau modèle",
    ],
    "Offres et financements": [
        "loA", "LLD", "financement", "leasing", "location", "crédit",
        "offre", "loyer", "prime", "bonus", "aide", "promotion",
    ],
    "Fiscalité et réglementation": [
        "malus", "bonus écologique", "fiscalité", "réglementation",
        "norme", "taxe", "immatriculation", "zfe", "zone à faibles émissions",
        "co2", "émissions", "contrôle technique",
    ],
    "Marché automobile": [
        "marché", "immatriculation", "vente", "ventes", "constructeur",
        "électrique", "hybride", "diesel", "essence", "automobile",
    ],
    "Concurrents et nouveaux modèles": [
        "renault", "peugeot", "citroën", "citroen", "volkswagen", "audi",
        "mercedes", "smart", "tesla", "volvo", "byd", "nouveau modèle",
        "nouvelle génération", "présente", "dévoile", "lancement",
    ],
}

HIGH_INTENT = [
    "offre", "financement", "loyer", "lld", "loa", "bonus", "malus",
    "prime", "prix", "tarif", "commande", "livraison", "rappel",
    "nouveau modèle", "nouvelle génération", "immatriculation",
    "réglementation", "zfe", "co2",
]

def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()

def first_text(item, names):
    for name in names:
        el = item.find(name)
        if el is not None and el.text:
            return clean(el.text)
    # RSS Atom
    for name in names:
        el = item.find("{http://www.w3.org/2005/Atom}" + name)
        if el is not None:
            if el.text:
                return clean(el.text)
            if name == "link":
                return el.attrib.get("href", "")
    return ""

def category_for(text):
    low = text.lower()
    scores = {
        topic: sum(1 for word in words if word.lower() in low)
        for topic, words in KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "Marché automobile"

def priority_for(text, topic):
    low = text.lower()
    if any(word in low for word in ["rappel de sécurité", "rappel constructeur", "malus", "bonus écologique", "nouvelle réglementation", "hausse des prix", "baisse des prix"]):
        return ("urgent", "Impact client")
    if topic in ("Offres et financements", "Fiscalité et réglementation", "MINI et BMW") or any(w in low for w in HIGH_INTENT):
        return ("important", "Utile en vente")
    return ("watch", "À suivre")

def parse_date(item):
    raw = first_text(item, ["pubDate", "date", "updated", "published"])
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                pass
    return None

def get_feed(source, url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "MINI-Assistant-NewsBot/1.0 (public RSS reader)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        data = response.read(2_500_000)
    root = ET.fromstring(data)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    results = []
    for item in items[:35]:
        title = first_text(item, ["title"])
        link = first_text(item, ["link", "guid", "id"])
        desc = first_text(item, ["description", "summary", "content:encoded", "encoded"])
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        date = parse_date(item)
        results.append({
            "title": title[:240],
            "url": link,
            "desc": desc[:420],
            "source": source,
            "published": date.isoformat() if date else "",
            "_date": date.timestamp() if date else 0,
        })
    return results

def main():
    articles = []
    feed_status = []
    for source, url in FEEDS:
        try:
            found = get_feed(source, url)
            articles.extend(found)
            feed_status.append({"source": source, "ok": True, "count": len(found)})
        except Exception as exc:
            print(f"Flux ignoré ({source}): {exc}")
            feed_status.append({"source": source, "ok": False, "count": 0})
    # Dédupliquer sur URL, puis sur titre normalisé.
    unique = {}
    for article in articles:
        key = article["url"].rstrip("/") or article["title"].lower()
        if key not in unique or article["_date"] > unique[key]["_date"]:
            unique[key] = article
    articles = list(unique.values())
    for a in articles:
        text = f'{a["title"]} {a["desc"]}'
        a["topic"] = category_for(text)
        a["priority"], a["label"] = priority_for(text, a["topic"])
        a["desc"] = a["desc"] or "Ouvrir la source pour consulter les détails. Vérifier les conditions et dates avant toute communication client."
        if a["_date"]:
            a["date"] = datetime.fromtimestamp(a["_date"], timezone.utc).strftime("%d/%m/%Y")
        else:
            a["date"] = "Date non précisée"
        del a["_date"]
    rank = {"urgent": 0, "important": 1, "watch": 2}
    articles.sort(key=lambda a: (rank.get(a["priority"], 9), -(
        datetime.fromisoformat(a["published"]).timestamp() if a.get("published") else 0
    )))
    # Limite raisonnable pour une page mobile.
    output = {
        "checkedAt": datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC"),
        "schedule": "Deux fois par jour",
        "feedStatus": feed_status,
        "articles": articles[:30],
    }
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(output['articles'])} articles enregistrés dans news.json.")

if __name__ == "__main__":
    main()
