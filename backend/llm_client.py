"""The one place the backend talks to a language model (Gemini).

Contract for `generate`:

- **Input:** a system instruction, one user message, and whether the reply must be JSON.
- **Work:** one `models.generateContent` request with a finite timeout. The key goes in a
  request header, never in the URL, so it cannot show up in a logged address.
- **Output:** the model's text.
- **Failure:** `LlmNotConfiguredError` when no key is set, `LlmRateLimitedError` on HTTP 429,
  `LlmServiceError` when the request fails or the service answers an error (HTTP 503 is
  retried twice first), and
  `LlmBadOutputError` when it answers with no usable text. No message carries the key, the
  request body, or the provider's raw error text.

The model never touches the database. Callers pass what it should see in the prompt, and
the backend decides what to do with what comes back.
"""

import time

import httpx

from config import gemini_api_key, gemini_model

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT_SECONDS = 45.0
MAX_OUTPUT_TOKENS = 1500
# The free tier answers 503 "high demand" in bursts. That is worth a short retry; a timeout,
# a 429, or any other error is not, so those fail at once.
MAX_503_RETRIES = 2
RETRY_DELAY_SECONDS = 2.0


class LlmError(Exception):
    """Base for every model failure."""


class LlmNotConfiguredError(LlmError):
    def __init__(self) -> None:
        super().__init__(
            "The model API key is not configured. Add GEMINI_API_KEY to the project's .env "
            "file and restart the backend."
        )


class LlmRateLimitedError(LlmError):
    def __init__(self) -> None:
        super().__init__(
            "The model service has reached its request limit. Wait a minute and try again."
        )


class LlmServiceError(LlmError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"The model service could not be reached ({detail}).")


class LlmBadOutputError(LlmError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


def generate(system: str, user: str, json_output: bool = False) -> str:
    """Ask the model one question and return its text. See the module contract."""
    api_key = gemini_api_key()
    if api_key is None:
        raise LlmNotConfiguredError()

    body: dict = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": MAX_OUTPUT_TOKENS},
    }
    if json_output:
        body["generationConfig"]["responseMimeType"] = "application/json"

    for attempt in range(MAX_503_RETRIES + 1):
        try:
            response = httpx.post(
                GEMINI_URL.format(model=gemini_model()),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=body,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise LlmServiceError(type(exc).__name__) from None
        if response.status_code != 503 or attempt == MAX_503_RETRIES:
            break
        time.sleep(RETRY_DELAY_SECONDS)

    if response.status_code == 429:
        raise LlmRateLimitedError()
    if response.status_code != 200:
        # The status only. The provider's error text can echo parts of the request.
        raise LlmServiceError(f"the model service answered {response.status_code}")

    try:
        payload = response.json()
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise LlmBadOutputError("The model returned no answer.") from None

    if not text:
        raise LlmBadOutputError("The model returned an empty answer.")
    return text
