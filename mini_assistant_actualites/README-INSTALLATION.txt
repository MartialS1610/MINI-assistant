# Actualités automatiques — MINI Assistant

## Fichiers
- `.github/workflows/refresh-news.yml` : lancement automatique deux fois par jour et lancement manuel.
- `scripts/update_news.py` : lit des flux RSS publics, déduplique les articles, catégorise et attribue une priorité.
- `news.json` : fichier lu par le site MINI Assistant.

## Publication
Copiez les trois éléments à la racine du dépôt `MartialS1610/MINI-assistant`, en conservant exactement l'arborescence :
- `.github/workflows/refresh-news.yml`
- `scripts/update_news.py`
- `news.json`

Puis ouvrez GitHub > Actions > « Actualites automobiles MINI Assistant » > Run workflow.
Après la fin du workflow, vérifiez que `news.json` contient des articles. GitHub Pages doit publier ce fichier à l'URL `/MINI-assistant/news.json`.

## Horaires
Le workflow est planifié à 06:15 et 18:15 UTC. Cela correspond à 08:15 et 20:15 en France pendant l'heure d'été, et 07:15 et 19:15 pendant l'heure d'hiver. GitHub Actions peut démarrer avec un retard variable.

## Important
- Les flux RSS sont publics et leur disponibilité/structure peut changer.
- Le classement est heuristique : relisez les informations importantes avant de les utiliser en rendez-vous client.
- Les actualités et offres ne sont pas des conseils juridiques ou des conditions commerciales officielles.
- GitHub Actions peut être désactivé après une longue période d'inactivité du dépôt. Le lancement manuel reste disponible.
