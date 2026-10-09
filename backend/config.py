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


# The chatbot's model provider. Only Gemini is wired; the key stays in the backend.
GEMINI_KEY_SETTING = "GEMINI_API_KEY"
GEMINI_MODEL_SETTING = "GEMINI_MODEL"
# On 2026-10-08 gemini-3.8-flash did not answer a one word prompt within 90 seconds, and
# gemini-3.6-flash answered 503 "high demand" or 429 on most requests. gemini-3.5-flash-lite
# answered every request in a few seconds, and the models page recommends it for new projects.
# Override with GEMINI_MODEL.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def gemini_api_key() -> str | None:
    """The configured Gemini key, or None when it is absent, empty, or whitespace."""
    value = os.getenv(GEMINI_KEY_SETTING, "").strip()
    return value or None


def gemini_model() -> str:
    """The model to call. GEMINI_MODEL in .env overrides the default."""
    return os.getenv(GEMINI_MODEL_SETTING, "").strip() or DEFAULT_GEMINI_MODEL


def llm_key_status() -> str:
    """Wording for the health check. Never includes the key itself."""
    return "key is configured" if gemini_api_key() else "key is not configured"
