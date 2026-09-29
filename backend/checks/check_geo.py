"""Mocked checks for geo_controller. No live request is ever made.

Run from the backend folder with the project interpreter:

    .venv\\Scripts\\python.exe checks\\check_geo.py

Every provider answer below is a labelled, hand-written sample. Nothing here
depends on how many hotels Geoapify really has near a ZIP code.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_KEY = "fake-key-for-checks-only"
os.environ["GEOAPIFY_API_KEY"] = TEST_KEY  # load_dotenv does not override an existing value

import httpx  # noqa: E402

import geo_controller as geo  # noqa: E402

results: list[tuple[str, bool, str]] = []
calls: list[tuple[str, dict]] = []


def record(name: str, ok: bool, observed: str) -> None:
    results.append((name, ok, observed))


def provider(geocode=None, places=None, geocode_status=200, places_status=200):
    """Replace httpx.get with a fake that answers each Geoapify endpoint separately."""

    def _get(url, params=None, timeout=None):
        calls.append((url, dict(params or {})))
        is_places = url == geo.PLACES_URL
        status = places_status if is_places else geocode_status
        body = (places if is_places else geocode) or {}
        request = httpx.Request("GET", f"{url}?apiKey={TEST_KEY}")
        return httpx.Response(status, request=request, json=body)

    geo.httpx.get = _get
    calls.clear()


def raising(exc):
    def _get(url, params=None, timeout=None):
        calls.append((url, dict(params or {})))
        raise exc

    geo.httpx.get = _get
    calls.clear()


def expect(exc_type, func, *args):
    """The exception raised by func(*args), or None if it raised nothing else."""
    try:
        func(*args)
    except exc_type as exc:
        return exc
    return None


def zip_hit(postcode="16802", **overrides):
    result = {"postcode": postcode, "country_code": "us", "lat": 40.8, "lon": -77.86, "city": "State College"}
    return {"results": [{**result, **overrides}]}


def place(place_id="p1", name="Sample Hotel", **overrides):
    properties = {
        "place_id": place_id,
        "name": name,
        "lat": 40.79,
        "lon": -77.85,
        "address_line2": "1 Main Street, State College, PA 16801",
        "distance": 968.4,
        "datasource": {"attribution": "© OpenStreetMap contributors"},
    }
    properties.update(overrides)
    return {"type": "Feature", "properties": properties}


def places_of(*features):
    return {"type": "FeatureCollection", "features": list(features)}


# ---- ZIP lookup --------------------------------------------------------------

provider(zip_hit())
found = geo.look_up_zip("16802")
record("ZIP lookup returns the requested postcode", found.postcode == "16802" and found.latitude == 40.8, str(found))

provider(zip_hit(postcode="16801"))
record("a different postcode is refused", expect(geo.LocationNotFoundError, geo.look_up_zip, "16802") is not None, "LocationNotFoundError")

provider(zip_hit(country_code="ca"))
record("a non US result is refused", expect(geo.LocationNotFoundError, geo.look_up_zip, "16802") is not None, "LocationNotFoundError")

provider({"results": []})
record("an unresolved ZIP is refused", expect(geo.LocationNotFoundError, geo.look_up_zip, "99999") is not None, "LocationNotFoundError")

bad = ("", "   ", "1234", "123456", "abcde", "1680a", "16 802", "16802.0", "-1680")
provider(zip_hit())
refused = all(expect(geo.InvalidZipError, geo.look_up_zip, value) is not None for value in bad)
record("input that is not five digits is refused before any request", refused and not calls, f"{len(bad)} inputs, {len(calls)} requests")

provider({"results": [{"postcode": "00501", "country_code": "us", "lat": 40.81, "lon": -73.04, "city": "Holtsville"}]})
padded = geo.look_up_zip("  00501 ")
record("spaces are trimmed and leading zeros kept", padded.postcode == "00501", str(padded))

# ---- Hotels near a ZIP -------------------------------------------------------

provider(zip_hit(), places_of(place("a", "First Inn"), place("b", "Second Inn", distance=1500)))
nearby = geo.hotels_near_zip("16802")
places_call = next(params for url, params in calls if url == geo.PLACES_URL)
record(
    "hotels are mapped from the response, nearest first",
    [h.name for h in nearby.hotels] == ["First Inn", "Second Inn"]
    and nearby.hotels[0].distance_m == 968
    and nearby.hotels[0].address == "1 Main Street, State College, PA 16801",
    str([(h.name, h.distance_m) for h in nearby.hotels]),
)
record(
    "the search is centred on the returned point, longitude first, within 5 km",
    places_call["filter"] == "circle:-77.86,40.8,5000" and places_call["bias"] == "proximity:-77.86,40.8",
    f"filter={places_call['filter']} bias={places_call['bias']}",
)
record(
    "only hotels are requested, one page",
    places_call["categories"] == "accommodation.hotel" and places_call["limit"] == geo.MAX_HOTELS,
    f"categories={places_call['categories']} limit={places_call['limit']}",
)
record("the provider's attribution is passed on", nearby.attribution == "© OpenStreetMap contributors", str(nearby.attribution))
record("a short page is not marked as possibly incomplete", nearby.may_have_more is False, f"may_have_more={nearby.may_have_more}")

provider(zip_hit(), places_of())
empty = geo.hotels_near_zip("16802")
record("no hotels nearby is a successful empty answer", empty.hotels == () and empty.omitted_count == 0, f"{len(empty.hotels)} hotels")

provider(zip_hit(postcode="16801"), places_of(place()))
refused_zip = expect(geo.LocationNotFoundError, geo.hotels_near_zip, "16802")
record(
    "an unestablished ZIP never becomes a search somewhere else",
    refused_zip is not None and all(url != geo.PLACES_URL for url, _ in calls),
    f"{len(calls)} request(s), none to Places",
)

provider(zip_hit(), None, places_status=500)
record("a Places failure is an error, not an empty list", expect(geo.LocationServiceError, geo.hotels_near_zip, "16802") is not None, "LocationServiceError")

provider(zip_hit(), None, places_status=429)
record("a rate limit is reported as such", expect(geo.RateLimitedError, geo.hotels_near_zip, "16802") is not None, "RateLimitedError")

provider(None, None, geocode_status=429)
record("a rate limit while resolving the ZIP is reported as such", expect(geo.RateLimitedError, geo.look_up_zip, "16802") is not None, "RateLimitedError")

def places_time_out() -> None:
    """The ZIP resolves, then the Places request times out."""

    def _get(url, params=None, timeout=None):
        calls.append((url, dict(params or {})))
        if url == geo.PLACES_URL:
            raise httpx.ConnectTimeout("timed out")
        return httpx.Response(200, request=httpx.Request("GET", url), json=zip_hit())

    geo.httpx.get = _get
    calls.clear()


places_time_out()
record("a Places timeout is an error, not an empty list", expect(geo.LocationServiceError, geo.hotels_near_zip, "16802") is not None, "LocationServiceError")

provider(zip_hit(), places_of(place("a", name=None), place("b", name="   ")))
unnamed = geo.hotels_near_zip("16802")
record("a hotel without a name is kept, with the name left empty", [h.name for h in unnamed.hotels] == [None, None], str([h.name for h in unnamed.hotels]))

provider(
    zip_hit(),
    places_of(place("keep"), place("no-coords", lat=None), place(None), place("bad-lon", lon=999), place("", name="empty id")),
)
partial = geo.hotels_near_zip("16802")
record(
    "places without an id or usable coordinates are left out and counted",
    [h.place_id for h in partial.hotels] == ["keep"] and partial.omitted_count == 4,
    f"kept={[h.place_id for h in partial.hotels]} omitted={partial.omitted_count}",
)

provider(zip_hit(), places_of(*[place(f"p{i}", f"Hotel {i}") for i in range(geo.MAX_HOTELS)]))
full = geo.hotels_near_zip("16802")
record("a full page is marked as possibly incomplete", full.may_have_more is True and len(full.hotels) == geo.MAX_HOTELS, f"may_have_more={full.may_have_more}")

provider(
    zip_hit(),
    places_of(
        place("a", website="javascript:alert(1)"),
        place("b", website="https://example.com/inn"),
        place("c", website="example.com"),
        place("d", distance=None),
    ),
)
odd = geo.hotels_near_zip("16802")
websites = [h.website for h in odd.hotels]
record(
    "only plain http or https websites are kept",
    websites == [None, "https://example.com/inn", None, None],
    str(websites),
)
record("a missing distance stays missing", odd.hotels[3].distance_m is None, str(odd.hotels[3].distance_m))

# ---- The key never leaks -----------------------------------------------------

os.environ["GEOAPIFY_API_KEY"] = "   "
provider(zip_hit(), places_of(place()))
missing = expect(geo.KeyNotConfiguredError, geo.hotels_near_zip, "16802")
record("a missing key is reported before any request", missing is not None and not calls, f"{len(calls)} requests")
os.environ["GEOAPIFY_API_KEY"] = TEST_KEY

messages = []
for status in (401, 429, 500):
    provider(zip_hit(), None, places_status=status)
    error = expect(geo.LocationError, geo.hotels_near_zip, "16802")
    messages.append(str(error))
record(
    "no error message carries the key or the request URL",
    all(TEST_KEY not in m and "http" not in m.lower() for m in messages),
    " | ".join(messages),
)

# ---- Report ------------------------------------------------------------------

width = max(len(name) for name, _, _ in results)
for name, ok, observed in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {observed}")

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
sys.exit(1 if failed else 0)
