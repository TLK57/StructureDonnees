import os
from dataclasses import dataclass


def _parse_bool(value, default=False):
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_collection_prefix():
    explicit_prefix = os.getenv("MONGODB_COLLECTION_PREFIX", "").strip()
    if explicit_prefix:
        normalized = explicit_prefix.upper()
        if not normalized.startswith("G_"):
            normalized = f"G_{normalized}"
        if not normalized.endswith("_"):
            normalized = f"{normalized}_"
        return normalized

    team_members = [member.strip() for member in os.getenv("TEAM_MEMBER_NAMES", os.getenv("USERNAME", "")).split(",")]
    initials = "".join(member[0].upper() for member in team_members if member)
    if initials:
        return f"G_{initials}_"

    return ""


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db_name: str
    mongodb_collection_prefix: str
    mongo_server_selection_timeout_ms: int
    flask_secret_key: str
    flask_debug: bool
    flask_host: str
    flask_port: int
    request_timeout_seconds: int
    image_request_timeout_seconds: int
    http_max_retries: int
    http_backoff_factor: float
    http_user_agent: str
    fetch_article_images: bool
    scheduler_enabled: bool
    scheduler_timezone: str


def load_settings():
    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "SD2026_projet"),
        mongodb_collection_prefix=_build_collection_prefix(),
        mongo_server_selection_timeout_ms=_parse_int(
            os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS"),
            2000,
        ),
        flask_secret_key=os.getenv("FLASK_SECRET_KEY", "dev-structure-donnees-secret"),
        flask_debug=_parse_bool(os.getenv("FLASK_DEBUG"), True),
        flask_host=os.getenv("FLASK_HOST", "127.0.0.1"),
        flask_port=_parse_int(os.getenv("FLASK_PORT"), 5000),
        request_timeout_seconds=_parse_int(os.getenv("REQUEST_TIMEOUT_SECONDS"), 10),
        image_request_timeout_seconds=_parse_int(os.getenv("IMAGE_REQUEST_TIMEOUT_SECONDS"), 10),
        http_max_retries=max(0, _parse_int(os.getenv("HTTP_MAX_RETRIES"), 2)),
        http_backoff_factor=max(0.0, _parse_float(os.getenv("HTTP_BACKOFF_FACTOR"), 0.5)),
        http_user_agent=os.getenv("HTTP_USER_AGENT", "StructureDonneesBot/1.0"),
        fetch_article_images=_parse_bool(os.getenv("FETCH_ARTICLE_IMAGES"), True),
        scheduler_enabled=_parse_bool(os.getenv("SCHEDULER_ENABLED"), True),
        scheduler_timezone=os.getenv("SCHEDULER_TIMEZONE", "UTC"),
    )
