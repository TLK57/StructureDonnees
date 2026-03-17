#Connexion à la base de données MongoDB

# 1. Import du client MongoDB depuis pymongo
from pymongo import MongoClient

# 2. Connexion au serveur MongoDB local
client = MongoClient("mongodb://localhost:27017")

# 3. Sélection de la base de données
db = client["SD2026_projet"]

# 4. Accès aux collections
subscriptions  = db["subscriptions"]
articles       = db["articles"]
consultations  = db["consultations"]

if __name__ == "__main__":
    try:
        # Vérifie que le serveur MongoDB répond
        client.admin.command("ping")
        print("Connexion MongoDB réussie !")
        print(f"Base de données : {db.name}")
        print(f"Collections disponibles : {db.list_collection_names()}")
    except Exception as e:
        print(f"Erreur de connexion : {e}")