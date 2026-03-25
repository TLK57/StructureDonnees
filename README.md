# StructureDonnees

Application web Flask qui recupere des titres d'actualite depuis des sitemaps XML, les stocke dans MongoDB, puis permet de consulter les articles et de generer un nuage de mots SVG a partir des titres.

## Prerequis

- Python 3.11 ou plus recent
- MongoDB accessible via une URI

## Installation

1. Creer un environnement virtuel.
2. Installer les dependances avec `pip install -r requirements.txt`.
3. Copier `.env.example` vers `.env` puis adapter les variables si besoin.

## Variables d'environnement principales

- `MONGODB_URI` : URI de connexion MongoDB.
- `MONGODB_DB_NAME` : nom de la base MongoDB.
- `TEAM_MEMBER_NAMES` : liste des membres separee par des virgules pour generer le prefixe des collections `G_..._`.
- `MONGODB_COLLECTION_PREFIX` : prefixe explicite des collections si vous voulez forcer la convention.
- `FLASK_DEBUG` : `true` ou `false`.
- `FLASK_HOST` et `FLASK_PORT` : adresse et port de demarrage.
- `REQUEST_TIMEOUT_SECONDS` : timeout des lectures de sitemap.
- `FETCH_ARTICLE_IMAGES` : active ou non la recuperation des images d'articles.
- `SCHEDULER_ENABLED` : active ou non la mise a jour automatique des abonnements.

## Lancer l'application

```bash
python src/main.py
```

Au demarrage, l'application cree automatiquement les index MongoDB necessaires.

## Lancer les tests

```bash
python -m unittest discover -s tests
```

## Structure

- `src/app.py` : routes Flask, logique de collecte et scheduler.
- `src/BdMongo.py` : connexion MongoDB et creation des index.
- `src/config.py` : lecture de la configuration via variables d'environnement.
- `src/templates/` : interfaces HTML.
- `tests/` : tests unitaires de base.
