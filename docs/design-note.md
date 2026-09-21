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
controller. Each route validates its input through the Pydantic models in
`schemas.py`, makes one controller call, and returns the result. Two
application-level handlers turn a missing record into a 404 and a missing CSV
into a readable 500, so no route contains a `try`/`except`.

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
