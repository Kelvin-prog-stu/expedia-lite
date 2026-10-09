# Schema check: API hotels against the Assignment 1 database

Recorded on 2026-10-01 on branch `assignment2_part2_in_class`, before any schema
change. The agent made these checks read-only at the student's request. Nothing in
the database or the code was changed.

- Database: `backend/expedia_lite.db`
- API response inspected: `GET /api/nearby-hotels?zip=16802`, which is what the
  browser's Network panel shows for the hotel search.

## The existing `hotels` table

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `hotel_id` | TEXT | primary key | Our own ids: `H001` to `H008` |
| `hotel_name` | TEXT | yes | |
| `city` | TEXT | yes | |
| `state` | TEXT | yes | |
| `nightly_rate_usd` | INTEGER | yes | One number per hotel |

Eight rows, all from the instructor's sample data: Harbor Lantern Hotel (150),
Maple Square Inn (120), Metro Garden Hotel (200), Riverside Studio Hotel (175),
Liberty Lane Inn (110), Museum Walk Hotel (140), Capitol Grove Hotel (160), and
Valley Trail Inn (100).

## What the API returns for one hotel

```json
{
  "place_id": "51268f029ffa7653c05961f0...(122 characters)",
  "name": "Scholar Hotel State College",
  "latitude": 40.7946313,
  "longitude": -77.8590467,
  "address": "205 East Beaver Avenue, State College, PA 16801, United States of America",
  "distance_m": 968,
  "website": "https://scholarstatecollege.com"
}
```

Around the hotels the response also carries `location`, `radius_m`, `limit`,
`may_have_more`, `omitted_count`, and `attribution`.

## API information against the database

| API information | API field | Matching database column |
| --- | --- | --- |
| Provider hotel ID | `place_id` | **Missing.** `hotels.hotel_id` is our own id (`H001`). The provider's id is a 122 character string. Putting it there would mix two id spaces, and nothing records which provider an id came from. |
| Hotel name | `name` | `hotels.hotel_name`. A match, with one catch: the column is required, but the provider can omit a name. |
| Address | `address` | **Missing as a whole address.** The table has `city` and `state` only, no street. |
| Latitude | `latitude` | **Missing.** The table has no coordinate columns. |
| Longitude | `longitude` | **Missing.** |

Also with no home in the table: `website`, and where and when the data was fetched.
`distance_m` is measured from one search's centre, so it should not be stored.

## Where prices come from

**The API supplies no price.** The shaped response has no price field. I also
checked the provider's raw response for the same ZIP: 20 hotels and 97 distinct
field paths, and none is a price. Two paths mention rooms or a fee, and neither
is a rate:

- `rooms` is a total room count for the building, present for 1 of 20 hotels. It
  is capacity, not rooms free on a date.
- `internet_access:fee` is `no` or absent. It says whether wifi costs extra, not a
  price.

`hotels.nightly_rate_usd` is Assignment 1 sample data for eight fictional hotels,
and it is required. An API hotel cannot be stored in `hotels` without inventing a
number, which the assignment forbids. So an API hotel's rate has to come from
somewhere else, and for this activity that is simulated classroom data, labelled as
such.

## Date-specific storage

**There is nowhere to store it.** The only date columns in the whole database are
`trips.check_in` and `trips.check_out`. Those describe fixed stays for the eight
sample hotels. They hold no rate and no room count, and `trips.hotel_id` is a
foreign key to `hotels.hotel_id`, so they cannot refer to an API hotel at all.

No table can hold a hotel, a date, that night's rate, and the number of rooms
available. A single `nightly_rate_usd` per hotel cannot say that Friday costs
more than Tuesday or that Saturday is nearly full.

## What is missing

1. **A table for saved API hotels**, keyed by the provider's id (unique), with a
   nullable name, latitude and longitude, an address, and when it was fetched. It
   must not reuse `hotels`, whose price column is required.
2. **A table of dated classroom rates and availability**, one row per saved hotel
   per night: hotel reference, date, nightly rate, rooms available. It needs a
   foreign key to the saved hotels and a rule that a hotel has one row per date.
3. **A link from the hotel list to that storage**, so each listed hotel can be
   matched by its provider id to its saved record and its rates.
4. **Labelling.** The rates and room counts are simulated classroom data, not the
   provider's prices or inventory, and the interface must say so.

Nothing needs to change in `hotels`, `trips`, `users`, `bookings`, or `app_meta`.
The Assignment 1 tables and the eight supplied hotels stay exactly as they are.
