"""Local settings for the backend, read from the project-root .env file.

The path is derived from this file, so the backend finds the same .env no
matter which working directory it was started from. The file is read once, at
import, which means the backend must be restarted after .env is edited.

Nothing here prints or logs a value. Callers ask for the key only at the moment
they make a request with it.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
GEOAPIFY_KEY_SETTING = "GEOAPIFY_API_KEY"

load_dotenv(ENV_PATH)


def geoapify_api_key() -> str | None:
    """The configured key, or None when it is absent, empty, or whitespace."""
    value = os.getenv(GEOAPIFY_KEY_SETTING, "").strip()
    return value or None


def geoapify_key_status() -> str:
    """Wording for the health check. Never includes the key itself."""
    return "key is configured" if geoapify_api_key() else "key is not configured"
