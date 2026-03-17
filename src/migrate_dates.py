#Migration des publication_date texte → datetime

from datetime import datetime, timezone
from BdMongo import articles

# Formats ISO courants rencontrés dans les sitemaps
FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]


def convertir_date(date_str):
    """Convertit une chaîne de date en datetime UTC. Retourne None si échec."""
    if not date_str or not isinstance(date_str, str):
        return None
    for fmt in FORMATS:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def migrer():
    nb_convertis = 0
    nb_invalides = 0
    nb_ignores   = 0

    # Récupère uniquement les articles dont publication_date est une chaîne
    # (les datetime MongoDB sont de type date, pas string)
    curseur = articles.find({"publication_date": {"$type": "string"}})

    for article in curseur:
        date_texte = article["publication_date"]
        date_dt    = convertir_date(date_texte)

        if date_dt is not None:
            # Mise à jour du document avec le vrai datetime
            articles.update_one(
                {"_id": article["_id"]},
                {"$set": {"publication_date": date_dt}}
            )
            nb_convertis += 1
        else:
            # La chaîne n'a pas pu être convertie : on la laisse en place
            print(f"  Invalide (ignoré) : '{date_texte}' — id={article['_id']}")
            nb_invalides += 1

    # Les articles dont publication_date est déjà un datetime ou None
    nb_ignores = articles.count_documents({
        "publication_date": {"$not": {"$type": "string"}}
    })

    print("\n── Résultat de la migration ──────────────────")
    print(f"  Convertis avec succès : {nb_convertis}")
    print(f"  Invalides (laissés)   : {nb_invalides}")
    print(f"  Déjà corrects         : {nb_ignores}")
    print("──────────────────────────────────────────────")


if __name__ == "__main__":
    print("Démarrage de la migration des dates...\n")
    migrer()
    print("\nMigration terminée.")