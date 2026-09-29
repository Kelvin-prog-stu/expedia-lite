# Design note

Who does what in Expedia Lite, and why the pieces are split this way.

## Model, View, Controller

The booking features follow the Model-View-Controller split discussed in class.

**Model (`backend/models.py`)** holds the data and its relationships. It
defines the four SQLite tables that mirror the supplied CSV files, with foreign
keys for the relationships in the data pack: a trip belongs to one hotel
(`trips.hotel_id`), and a booking connects one traveler to one trip
(`bookings.user_id`, `bookings.trip_id`). A `CHECK` constraint limits a
booking's status to `confirmed` or `cancelled`.

**View (`frontend/src/`)** presents the interface. `App.vue` lays out the page
and holds the interaction state; `SearchResults.vue`, `BookingHistory.vue`, and
`DateRangePicker.vue` are the pieces a person works with. The view never touches
the database or builds a URL: every request goes through `src/api.js`.

**Controller (`backend/database_controller.py`)** performs every create, read,
update, and delete against SQLite, and nothing else runs SQL. It imports nothing
from FastAPI, so the booking rules can be exercised without a running server.

**FastAPI (`backend/main.py`)** is the boundary between the view and the
controller. Its routes handle requests: they receive each action from the View
and pass the work to the database controller. Each route validates its input
through the Pydantic models in `schemas.py`, makes one controller call, and
returns the result. Two application-level handlers turn a missing record into a
404 and a missing CSV into a readable 500, so no route contains a
`try`/`except`.

## Data lifecycle

On the first start, `seed.py` loads the four CSV files into
`backend/expedia_lite.db`, keeping their IDs, and writes a `seeded` marker into
an `app_meta` table. Every later start sees the marker and leaves the data
alone. That is what lets saved bookings survive a restart without the starter
records being duplicated or reloaded.

New bookings take the next number after the highest supplied ID, so the first
one is `B007`. The next number is stored in `app_meta` rather than worked out
from the rows present, which means an ID is never reused, even after the
booking holding it is deleted.

Cancelling changes a booking's status and keeps the row, so it stays in
history. Deleting removes the row.

## CRUD, end to end

| Action | View | Route | Controller |
| --- | --- | --- | --- |
| Create | Book button on a stay | `POST /api/bookings` | `create_booking` |
| Read | Booking history | `GET /api/bookings?user_id=` | `list_bookings` |
| Update | Cancel button | `PATCH /api/bookings/{id}` | `cancel_booking` |
| Delete | Delete, then Confirm delete | `DELETE /api/bookings/{id}` | `delete_booking` |

Search runs the same way: `GET /api/hotels?name=` calls `search_hotels`, which
now queries SQLite instead of reading the CSV files.

## Controller contracts

What each database controller function expects and returns. A failure raises
`RecordNotFoundError`, which FastAPI returns as a 404 with the message shown,
and nothing is written.

| Function | Input | Output | Failure |
| --- | --- | --- | --- |
| `search_hotels` | Part of a hotel name | Matching hotels, each with its stays | None; no match is an empty list |
| `list_bookings` | A `user_id`, or none for all | Bookings joined to traveler, stay, and hotel, newest first | None; an unknown traveler has an empty history |
| `create_booking` | An existing `user_id` and `trip_id` | The saved booking with its new `booking_id`, `confirmed`, booked today | `No traveler with ID U999.` or `No stay with ID T999.` |
| `cancel_booking` | An existing `booking_id` | The same booking, now `cancelled` | `No booking with ID B999.` |
| `delete_booking` | An existing `booking_id` | Nothing; the row is gone | `No booking with ID B999.` |

## Request flow

```
[Person presses Book on a stay]
          |
          v
[frontend/src/components/SearchResults.vue]   View
          |
          | emits book -> App.vue -> createBooking('U006', 'T001')
          v
[frontend/src/api.js]                         request boundary
          |
          | POST /api/bookings {"user_id":"U006","trip_id":"T001"}
          v
[Vite dev server :5173] -- proxy --> [backend/main.py]   FastAPI route
                                            |
                                            | db.create_booking('U006', 'T001')
                                            v
                               [backend/database_controller.py]   Controller
                                            |
                                            | INSERT INTO bookings ...
                                            v
                               [expedia_lite.db, tables from models.py]   Model
                                            |
                                            v
                  201 {"booking_id":"B007", ..., "status":"confirmed"}
                                            |
                                            v
                  [BookingHistory.vue shows B007 as confirmed]
```

## Why the proxy rather than CORS

Vite forwards `/api` to port 8000 in development, so the frontend holds no
backend hostname anywhere and requests stay same-origin. `main.py` still
installs CORS middleware for any client that calls port 8000 directly; under the
proxy it never fires.

## Interface

The layout comes from the research in `docs/ui-research.md`: Expedia as the base,
Priceline's two-month calendar, and Booking.com as the example of what to avoid.
Dates are a planning aid, since every stay has fixed dates, and the page states
that under the search row.

## Live hotel search (Assignment 2, Part 1)

A second search runs beside the booking features and shares none of their
storage. It answers "which hotels are near this ZIP code?" from a public API
instead of the SQLite tables.

| Layer | File | Job |
| --- | --- | --- |
| View | `ZipLookupPanel.vue` | The ZIP form, its validation message, the location table, and the unresolved or failed message |
| View | `NearbyHotels.vue` | The loading placeholders, the summary, the empty message, and the credits |
| View | `HotelList.vue`, `HotelMap.vue` | The numbered list and the Leaflet map, both driven by one selected `place_id` |
| View | `App.vue`, `api.js` | Holds the selection and the state; `api.js` is the only place that calls `fetch` |
| Route | `main.py` | `GET /api/nearby-hotels?zip=` makes one controller call and maps each error to a status code |
| Controller | `geo_controller.py` | The only module that talks to Geoapify; its contract is written at the top of the file |
| Model | `schemas.py` | `ZipLocation`, `NearbyHotel`, and `NearbyHotelsResponse` |

```
[ZIP typed, Find location pressed]      ZipLookupPanel.vue        View
        |  five digits? no -> message, no request
        v
findNearbyHotels('16802')               frontend/src/api.js
        |  GET /api/nearby-hotels?zip=16802   (Vite proxies to :8000)
        v
find_nearby_hotels                      backend/main.py           Route
        |  geo.hotels_near_zip('16802')
        v
look_up_zip -> Geoapify geocoding       geo_controller.py         Controller
        |  postcode and US country must match, or LocationNotFoundError
        v
hotels_near_zip -> Geoapify places      circle:lon,lat,5000, nearest first, one page
        |
        v
NearbyHotelsResponse: location, hotels, may_have_more, omitted_count, attribution
        |
        v
HotelList.vue and HotelMap.vue          the same place_id selects in both
```

The Geoapify key lives in `.env`, is read by `config.py`, and is added to the
outgoing request inside `geo_controller.py`. It is never returned, logged, or
placed in an error message, and the map's tiles need none.

### The data structure

A `NearbyHotel` is deliberately not the sample `Hotel`, which needs a nightly
rate the provider does not have:

| Field | Meaning | When absent |
| --- | --- | --- |
| `place_id` | The provider's identifier, used to pair list and map | The result is left out and counted in `omitted_count` |
| `latitude`, `longitude` | Where the pin goes | The result is left out and counted |
| `name` | The place's name | `null`; the interface says "Name not provided" |
| `address` | The provider's address line | `null`; the line is not shown |
| `distance_m` | Metres from the ZIP centre | `null`; the line is not shown |
| `website` | Only a plain http or https address | `null`; no link |

### Failure is not emptiness

| What happened | Status | Interface |
| --- | --- | --- |
| Not five digits | 400 (and blocked in the browser first) | Inline message, no request |
| The provider cannot place the ZIP | 404 | "ZIP code not found" |
| Placed, but no hotels within 5 km | 200 with an empty list | "No hotels found", map and centre still shown |
| The request limit was reached | 429 | "Too many requests" |
| The provider failed or timed out | 502 | "Could not load hotels" |
| No key configured | 503 | The message says to add the key |
| The backend is down | proxy 500 or no answer | "Backend not reachable" |
