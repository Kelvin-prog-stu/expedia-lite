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
  provider has no usable match for that ZIP, `RateLimitedError` when the
  provider says its request limit was reached, and `LocationServiceError` when
  the request itself fails. Only a valid ZIP reaches the provider. No message
  carries the key, the request URL, or raw provider exception text, because the
  key travels in the query string.

Contract for `hotels_near_zip`:

- **Input:** the same five digit ZIP code.
- **Work:** resolves the ZIP with `look_up_zip`, then asks Geoapify Places for
  hotels within `SEARCH_RADIUS_METERS` of *the point that lookup returned*. The
  search centre is that point, not the traveler's position and not every address
  in the ZIP area. If the ZIP is not established, no places request is made, so a
  failed lookup can never turn into a search around somewhere else.
- **Output:** `NearbyHotels`: the resolved location, the radius, the page size,
  whether the page was full (`may_have_more`), how many results were left out
  for lacking an identifier or coordinates, the provider's attribution text, and
  the hotels nearest first. A hotel carries only what the provider returned: an
  id, a name, coordinates, an address, and a distance and website when present.
  There are no prices, ratings, or availability, because the provider has none.
  An empty list is a successful search that found nothing nearby.
- **Failure:** the same errors as `look_up_zip`. A provider failure is never
  reported as an empty result.

This module imports nothing from FastAPI and touches no database, so the lookup
can be exercised on its own. It is separate from the Hotel model, which needs a
price; a place is only a point on the map.
"""

import re
from dataclasses import dataclass

import httpx

from config import geoapify_api_key

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
REQUEST_TIMEOUT_SECONDS = 8.0
COUNTRY_CODE = "us"

HOTEL_CATEGORY = "accommodation.hotel"
SEARCH_RADIUS_METERS = 5000
# One page of nearest results. A full page means there may be more within the radius.
MAX_HOTELS = 20

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


@dataclass(frozen=True)
class NearbyHotel:
    """One place the provider calls a hotel. Optional fields are None when absent."""

    place_id: str
    name: str | None
    latitude: float
    longitude: float
    address: str | None
    distance_m: int | None
    website: str | None


@dataclass(frozen=True)
class NearbyHotels:
    location: ZipLocation
    radius_m: int
    limit: int
    may_have_more: bool
    omitted_count: int
    attribution: str | None
    hotels: tuple[NearbyHotel, ...]


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


class RateLimitedError(LocationError):
    def __init__(self) -> None:
        super().__init__(
            "The location service has reached its request limit. Try again in a few minutes."
        )


class LocationServiceError(LocationError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"The location service could not be reached ({detail}).")


def look_up_zip(postcode: str) -> ZipLocation:
    """Resolve a United States ZIP code to a point. See the module contract."""
    zip_code = _validated_zip(postcode)
    payload = _get_json(
        GEOCODE_URL,
        {
            "postcode": zip_code,
            "type": "postcode",
            "filter": f"countrycode:{COUNTRY_CODE}",
            "format": "json",
        },
    )
    return _first_usable_match(payload, zip_code)


def hotels_near_zip(postcode: str) -> NearbyHotels:
    """Hotels within the search radius of the point a ZIP code resolves to."""
    location = look_up_zip(postcode)
    centre = f"{location.longitude},{location.latitude}"  # Geoapify wants longitude first.
    payload = _get_json(
        PLACES_URL,
        {
            "categories": HOTEL_CATEGORY,
            "filter": f"circle:{centre},{SEARCH_RADIUS_METERS}",
            "bias": f"proximity:{centre}",
            "limit": MAX_HOTELS,
        },
    )
    return _nearby_hotels(payload, location)


def _validated_zip(postcode: str) -> str:
    zip_code = postcode.strip()
    if not ZIP_PATTERN.fullmatch(zip_code):
        raise InvalidZipError(postcode)
    return zip_code


def _get_json(url: str, params: dict[str, object]) -> object:
    """One provider request. The key is added here and never appears in an error."""
    api_key = geoapify_api_key()
    if api_key is None:
        raise KeyNotConfiguredError()

    try:
        response = httpx.get(
            url, params={**params, "apiKey": api_key}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        # The status only. The request URL carries the key, so it is never repeated.
        if exc.response.status_code == 429:
            raise RateLimitedError() from None
        raise LocationServiceError(f"the provider answered {exc.response.status_code}") from None
    except (httpx.HTTPError, ValueError) as exc:
        raise LocationServiceError(type(exc).__name__) from None


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


def _nearby_hotels(payload: object, location: ZipLocation) -> NearbyHotels:
    """Shape a Places response. A place without an id or coordinates is left out."""
    features = payload.get("features") if isinstance(payload, dict) else None
    features = features if isinstance(features, list) else []

    hotels: list[NearbyHotel] = []
    attributions: list[str] = []

    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue

        hotel = _hotel_from(properties)
        if hotel is not None:
            hotels.append(hotel)
            _remember_attribution(properties, attributions)

    return NearbyHotels(
        location=location,
        radius_m=SEARCH_RADIUS_METERS,
        limit=MAX_HOTELS,
        may_have_more=len(features) >= MAX_HOTELS,
        omitted_count=len(features) - len(hotels),
        attribution="; ".join(attributions) or None,
        hotels=tuple(hotels),
    )


def _hotel_from(properties: dict) -> NearbyHotel | None:
    place_id = properties.get("place_id")
    latitude, longitude = _coordinates(properties)
    if not isinstance(place_id, str) or not place_id.strip():
        return None
    if latitude is None or longitude is None:
        return None

    return NearbyHotel(
        place_id=place_id.strip(),
        name=_text(properties.get("name")),
        latitude=latitude,
        longitude=longitude,
        address=_text(properties.get("address_line2")) or _text(properties.get("formatted")),
        distance_m=_distance(properties.get("distance")),
        website=_web_address(properties.get("website")),
    )


def _remember_attribution(properties: dict, attributions: list[str]) -> None:
    source = properties.get("datasource")
    text = _text(source.get("attribution")) if isinstance(source, dict) else None
    if text and text not in attributions:
        attributions.append(text)


def _coordinates(result: dict) -> tuple[float | None, float | None]:
    """Latitude and longitude when both are real numbers in range."""
    latitude, longitude = result.get("lat"), result.get("lon")

    for value, limit in ((latitude, 90), (longitude, 180)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, None
        if not -limit <= value <= limit:
            return None, None

    return float(latitude), float(longitude)


def _text(value: object) -> str | None:
    """A stripped, non-empty string, or None."""
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _distance(value: object) -> int | None:
    """Metres as a whole number, or None when the provider gave none."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return round(value)


def _web_address(value: object) -> str | None:
    """A website only when it is a plain http or https address."""
    text = _text(value)
    return text if text and re.match(r"https?://", text, re.IGNORECASE) else None


def _locality(result: dict) -> str | None:
    """The most specific place name the provider offers, if any."""
    for field in ("city", "town", "village", "suburb", "county"):
        value = _text(result.get(field))
        if value:
            return value
    return None
