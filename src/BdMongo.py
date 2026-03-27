from pymongo import ASCENDING, DESCENDING, IndexModel, MongoClient
from pymongo.errors import BulkWriteError, PyMongoError

from config import load_settings


SETTINGS = load_settings()

LEGACY_COLLECTION_NAMES = {
    "subscriptions": "subscriptions",
    "articles": "articles",
    "consultations": "consultations",
    "users": "users",
}


def build_collection_name(logical_name):
    if SETTINGS.mongodb_collection_prefix:
        return f"{SETTINGS.mongodb_collection_prefix}{logical_name}"
    return LEGACY_COLLECTION_NAMES[logical_name]

client = MongoClient(
    SETTINGS.mongodb_uri,
    connect=False,
    serverSelectionTimeoutMS=SETTINGS.mongo_server_selection_timeout_ms,
    tz_aware=True,
)
db = client[SETTINGS.mongodb_db_name]

subscriptions = db[build_collection_name("subscriptions")]
articles = db[build_collection_name("articles")]
consultations = db[build_collection_name("consultations")]
users = db[build_collection_name("users")]


def migrate_legacy_collection(logical_name, target_collection):
    legacy_name = LEGACY_COLLECTION_NAMES[logical_name]
    if target_collection.name == legacy_name:
        return

    legacy_collection = db[legacy_name]
    if legacy_collection.estimated_document_count() == 0:
        return

    if target_collection.estimated_document_count() > 0:
        return

    documents = list(legacy_collection.find())
    if not documents:
        return

    try:
        target_collection.insert_many(documents, ordered=False)
    except BulkWriteError:
        pass


def ensure_collection_compatibility():
    migrate_legacy_collection("subscriptions", subscriptions)
    migrate_legacy_collection("articles", articles)
    migrate_legacy_collection("consultations", consultations)
    migrate_legacy_collection("users", users)


def remove_duplicate_articles():
    """Supprime les articles en doublon, conservant le premier de chaque URL."""
    pipeline = [
        {
            "$group": {
                "_id": "$url",
                "first_id": {"$first": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {"count": {"$gt": 1}}
        }
    ]
    
    duplicates = list(articles.aggregate(pipeline))
    
    if not duplicates:
        return
    
    deleted_count = 0
    for dup in duplicates:
        # Supprimer tous les doublons sauf le premier (_id)
        result = articles.delete_many({
            "url": articles.find_one({"_id": dup["first_id"]})["url"],
            "_id": {"$ne": dup["first_id"]}
        })
        deleted_count += result.deleted_count
    
    if deleted_count > 0:
        print(f"⚠️ {deleted_count} article(s) en doublon supprimé(s)")


def ensure_indexes():
    try:
        ensure_collection_compatibility()
        remove_duplicate_articles()
        subscriptions.create_indexes(
            [
                IndexModel([("sitemap_url", ASCENDING)], unique=True, name="subscriptions_sitemap_url_unique"),
                IndexModel([("active", ASCENDING), ("source_name", ASCENDING)], name="subscriptions_active_source_idx"),
            ]
        )
        articles.create_indexes(
            [
                IndexModel([("url", ASCENDING)], unique=True, name="articles_url_unique"),
                IndexModel([("publication_date", DESCENDING)], name="articles_publication_date_idx"),
                IndexModel([("source_name", ASCENDING), ("publication_date", DESCENDING)], name="articles_source_publication_idx"),
            ]
        )
        consultations.create_indexes(
            [
                IndexModel([("article_id", ASCENDING)], name="consultations_article_id_idx"),
                IndexModel([("consulted_at", DESCENDING)], name="consultations_consulted_at_idx"),
                IndexModel([("user_id", ASCENDING)], name="consultations_user_id_idx"),
                IndexModel(
                    [("user_id", ASCENDING), ("consulted_at", DESCENDING)],
                    name="consultations_user_id_consulted_at_idx",
                ),
                IndexModel(
                    [("consulted_at", DESCENDING), ("article_id", ASCENDING)],
                    name="consultations_consulted_at_article_id_idx",
                ),
            ]
        )
        users.create_indexes(
            [
                IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique"),
                IndexModel([("username", ASCENDING)], unique=True, name="users_username_unique"),
            ]
        )
    except PyMongoError as exc:
        raise RuntimeError(f"Impossible de creer les index MongoDB: {exc}") from exc


def ping_database():
    client.admin.command("ping")


if __name__ == "__main__":
    try:
        ping_database()
        ensure_indexes()
        print("Connexion MongoDB reussie !")
        print(f"Base de donnees : {db.name}")
        print(f"Collections disponibles : {db.list_collection_names()}")
        print(f"Prefixe de collections : {SETTINGS.mongodb_collection_prefix or 'legacy'}")
    except Exception as exc:
        print(f"Erreur de connexion : {exc}")
