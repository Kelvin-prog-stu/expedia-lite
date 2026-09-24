"""Controller for location lookups against Geoapify, a public API.

Contract for `look_up_zip`:

- **Input:** a five digit United States ZIP code, for example `16802`. Leading
  zeros matter, so a ZIP is a string throughout, never a number.
- **Work:** asks Geoapify forward geocoding for that postcode, with a finite
  timeout, supplying the API key from `config.py`. An answer counts only when it
  names the same postcode, in the United States, with usable coordinates.
- **Output:** a `ZipLocation`: postcode, country code, latitude, longitude, and
  the locality when the provider gives one.
- **Failure:** `InvalidZipError` when the input is not five digits,
  `KeyNotConfiguredError` when no key is set, `LocationNotFoundError` when the
  provider has no usable match for that ZIP, and `LocationServiceError` when the
  request itself fails. Only a valid ZIP reaches the provider. No message
  carries the key, the request URL, or raw provider exception text, because the
  key travels in the query string.

This module imports nothing from FastAPI and touches no database, so the lookup
can be exercised on its own. It is separate from the Hotel model, which needs a
price; a location is only a point on the map.
"""

import re
from dataclasses import dataclass

import httpx

from config import geoapify_api_key

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
REQUEST_TIMEOUT_SECONDS = 8.0
COUNTRY_CODE = "us"

# Exactly five digits. A ZIP stays a string so 00501 keeps its leading zeros.
ZIP_PATTERN = re.compile(r"\d{5}")


@dataclass(frozen=True)
class ZipLocation:
    """One resolved postcode. `locality` is absent when the provider omits it."""

    postcode: str
    country_code: str
    latitude: float
    longitude: float
    locality: str | None


class LocationError(Exception):
    """Base for every failure this controller reports."""


class InvalidZipError(LocationError):
    def __init__(self, received: str) -> None:
        shown = received.strip()[:12] or "nothing"
        super().__init__(f"A ZIP code is five digits, for example 16802. Received {shown}.")
        self.received = received


class KeyNotConfiguredError(LocationError):
    def __init__(self) -> None:
        super().__init__(
            "The Geoapify API key is not configured. Add GEOAPIFY_API_KEY to the "
            "project's .env file and restart the backend."
        )


class LocationNotFoundError(LocationError):
    def __init__(self, postcode: str) -> None:
        super().__init__(f"No United States location found for ZIP {postcode}.")
        self.postcode = postcode


class LocationServiceError(LocationError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"The location service could not be reached ({detail}).")


def look_up_zip(postcode: str) -> ZipLocation:
    """Resolve a United States ZIP code to a point. See the module contract."""
    zip_code = postcode.strip()
    if not ZIP_PATTERN.fullmatch(zip_code):
        raise InvalidZipError(postcode)

    api_key = geoapify_api_key()
    if api_key is None:
        raise KeyNotConfiguredError()

    params = {
        "postcode": zip_code,
        "type": "postcode",
        "filter": f"countrycode:{COUNTRY_CODE}",
        "format": "json",
        "apiKey": api_key,
    }

    try:
        response = httpx.get(GEOCODE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        # The status only. The request URL carries the key, so it is never repeated.
        raise LocationServiceError(f"the provider answered {exc.response.status_code}") from None
    except (httpx.HTTPError, ValueError) as exc:
        raise LocationServiceError(type(exc).__name__) from None

    return _first_usable_match(payload, zip_code)


def _first_usable_match(payload: object, postcode: str) -> ZipLocation:
    """The first result naming this postcode in the US with real coordinates."""
    results = payload.get("results") if isinstance(payload, dict) else None

    for result in results or []:
        if not isinstance(result, dict):
            continue
        if str(result.get("postcode", "")).strip() != postcode:
            continue
        if str(result.get("country_code", "")).strip().lower() != COUNTRY_CODE:
            continue

        latitude, longitude = _coordinates(result)
        if latitude is None or longitude is None:
            continue

        return ZipLocation(
            postcode=postcode,
            country_code=COUNTRY_CODE.upper(),
            latitude=latitude,
            longitude=longitude,
            locality=_locality(result),
        )

    raise LocationNotFoundError(postcode)


def _coordinates(result: dict) -> tuple[float | None, float | None]:
    """Latitude and longitude when both are real numbers in range."""
    latitude, longitude = result.get("lat"), result.get("lon")

    for value, limit in ((latitude, 90), (longitude, 180)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, None
        if not -limit <= value <= limit:
            return None, None

    return float(latitude), float(longitude)


def _locality(result: dict) -> str | None:
    """The most specific place name the provider offers, if any."""
    for field in ("city", "town", "village", "suburb", "county"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
