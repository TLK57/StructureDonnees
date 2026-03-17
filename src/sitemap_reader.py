#Lecture d'un sitemap XML depuis une URL

# 1. Imports nécessaires
import requests                        # pour télécharger le sitemap
import xml.etree.ElementTree as ET    # pour analyser le XML

# 2. URL du sitemap à lire
SITEMAP_URL = "https://www.lemonde.fr/sitemap_news.xml"

# 3. Déclaration des namespaces XML
NAMESPACES = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news":    "http://www.google.com/schemas/sitemap-news/0.9",
}


def lire_sitemap(url):
    """
    Télécharge et analyse un sitemap XML.
    Retourne une liste de dictionnaires contenant les infos de chaque article.
    """

    # 4. Téléchargement du sitemap
    print(f"Téléchargement du sitemap : {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # lève une erreur si le téléchargement échoue

    # 5. Analyse du contenu XML
    root = ET.fromstring(response.content)

    articles = []

    # 6. Parcours de chaque balise <url> dans le sitemap
    for url_tag in root.findall("sitemap:url", NAMESPACES):

        # Extraction de la balise <loc> (lien de l'article)
        loc = url_tag.findtext("sitemap:loc", default="", namespaces=NAMESPACES)

        # Extraction de la balise <news:title>
        title = url_tag.findtext("news:news/news:title", default="", namespaces=NAMESPACES)

        # Extraction de la balise <news:publication_date>
        date = url_tag.findtext("news:news/news:publication_date", default="", namespaces=NAMESPACES)

        # Ajout de l'article dans la liste
        articles.append({
            "loc":   loc,
            "title": title,
            "publication_date":  date,
        })

    return articles


# 7. Test direct : affiche les 5 premiers articles
if __name__ == "__main__":
    articles = lire_sitemap(SITEMAP_URL)

    print(f"\n{len(articles)} articles trouvés au total.")
    print("--- 5 premiers articles ---\n")

    for article in articles[:5]:
        print(f"Titre : {article['title']}")
        print(f"Date  : {article['publication_date']}")
        print(f"URL   : {article['loc']}")
        print("-" * 60)