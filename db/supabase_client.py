import os
from functools import lru_cache
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseConfigError(RuntimeError):
    pass


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SupabaseConfigError(f"Missing required environment variable: {name}")
    return value


def is_supabase_enabled() -> bool:
    """Feature flag for cutover. Set USE_SUPABASE=false to force local mode."""
    raw = os.getenv("USE_SUPABASE", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Returns a singleton Supabase client.
    Requires:
      - SUPABASE_URL
      - SUPABASE_SERVICE_ROLE_KEY
    """
    url = _get_required_env("SUPABASE_URL")
    key = _get_required_env("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)