import os


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_database_url() -> str:
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "app")
    user = os.getenv("POSTGRES_USER", "app")
    password = _require_env("POSTGRES_PASSWORD")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
