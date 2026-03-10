# ============================================================
# sitemap_to_mongo.py - Lecture du sitemap et insertion dans MongoDB
# ============================================================

# 1. Imports nécessaires
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError

# 2. Import des collections depuis BdMongo.py
from BdMongo import articles, subscriptions

# 3. Configuration
SITEMAP_URL = "https://www.lemonde.fr/sitemap_news.xml"
SOURCE_NAME = "Le Monde"

# 4. Récupération du subscription_id depuis la collection subscriptions
#    On cherche l'abonnement correspondant à "Le Monde"
subscription = subscriptions.find_one({"source_name": SOURCE_NAME})
if subscription is None:
    raise ValueError(f"Aucun abonnement trouvé pour '{SOURCE_NAME}' dans la collection subscriptions.")
SUBSCRIPTION_ID = subscription["_id"]

# 5. Namespaces XML du sitemap
NAMESPACES = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news":    "http://www.google.com/schemas/sitemap-news/0.9",
}


def lire_sitemap(url):
    """Télécharge et parse le sitemap. Retourne une liste de dictionnaires."""

    print(f"Téléchargement du sitemap : {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    resultats = []

    for url_tag in root.findall("sitemap:url", NAMESPACES):
        loc              = url_tag.findtext("sitemap:loc",                     default="", namespaces=NAMESPACES)
        title            = url_tag.findtext("news:news/news:title",            default="", namespaces=NAMESPACES)
        publication_date = url_tag.findtext("news:news/news:publication_date", default="", namespaces=NAMESPACES)

        resultats.append({
            "loc":              loc,
            "title":            title,
            "publication_date": publication_date,  # même nom partout
        })

    return resultats


def inserer_articles(liste_articles):
    """
    Insère les articles dans MongoDB.
    Ignore les doublons grâce à l'index unique sur le champ 'url'.
    """

    nb_inseres  = 0
    nb_doublons = 0

    for item in liste_articles:

        # 6. Construction du document à insérer
        document = {
            "subscription_id":    SUBSCRIPTION_ID,       # ObjectId réel depuis subscriptions
            "source_name":        SOURCE_NAME,
            "url":                item["loc"],
            "title":              item["title"],
            "publication_date":   item["publication_date"],
            "fetched_at":         datetime.now(timezone.utc),
            "consultations_count": 0,
        }

        try:
            # 7. Tentative d'insertion
            articles.insert_one(document)
            nb_inseres += 1

        except DuplicateKeyError:
            # 8. L'URL existe déjà → on ignore sans planter
            nb_doublons += 1

    return nb_inseres, nb_doublons


# 9. Exécution principale
if __name__ == "__main__":

    liste = lire_sitemap(SITEMAP_URL)
    print(f"{len(liste)} articles lus dans le sitemap.")

    inseres, doublons = inserer_articles(liste)

    print(f"\n--- Résultat de l'insertion ---")
    print(f"Articles lus     : {len(liste)}")
    print(f"Articles insérés : {inseres}")
    print(f"Doublons ignorés : {doublons}")