# Research notes: live hotel search and map (Assignment 2, Part 1)

Written on 2026-09-29, before any list or map code for this part was written.
Each observation below was made on the date shown, by loading the page or
reading the documentation, not from memory. Where something could not be
observed, the note says so.

## Sources

| Source | What it was used for |
| --- | --- |
| Expedia hotel search, State College, Oct 9 to 11, 2026 (https://www.expedia.com/Hotel-Search) | How a large site lays out a hotel list and reaches its map |
| Booking.com search results and map view, State College (https://www.booking.com/searchresults.html) | A list and map shown together |
| Geoapify Places API (https://apidocs.geoapify.com/docs/places/) | Request format and response fields for hotels near a point |
| Geoapify Geocoding API (https://apidocs.geoapify.com/docs/geocoding/forward-geocoding/) | Resolving a ZIP code to a point |
| Leaflet reference (https://leafletjs.com/reference.html) | Markers, keyboard behaviour, attribution |
| OpenStreetMap tile usage policy (https://operations.osmfoundation.org/policies/tiles/) | Whether the standard tiles can be used, and on what terms |

## What the other sites do

### Expedia (observed 2026-09-29)

Useful:

- The result count sits above the list ("27 properties"), so the traveler knows
  how much there is before scrolling.
- The list card leads with the name, then the place, then a few short facts.
- A "View in a map" thumbnail gives the map a discoverable entry point.

Problems:

- **The map is a separate full-screen overlay**, opened from a thumbnail beside
  the filters. The list and the map are not on screen together in that view, so
  there is no way to see which pin is which card. The overlay stayed blank grey
  in my automated browser session, so I could not observe its pin behaviour and
  make no claim about it.
- **Results are not close to the search.** Several listed properties are marked
  12 to 32 miles from State College, next to ones in the town.
- **It mixes hotels with rental homes** under "All stays", and labels some cards
  "Ad" among the results.
- **Urgency and price claims** ("We have 6 left at this price", "$1,100 nightly")
  are the kind of content this project must not invent: the data source has no
  prices or availability.

### Booking.com (observed 2026-09-29)

Useful:

- **Filters, list, and map are side by side.** The list column and the map share
  the screen, so each card can be matched to the map.
- **Skeleton placeholders** (grey blocks in the shape of cards) show while the
  list loads, which separates "still loading" from "empty".
- The map has zoom buttons, a scale bar (5 km at the default view), and a map
  data credit in its corner.
- A "Close map" control and a "Search on map" box.

Problems:

- The default view was zoomed out to roughly 30 miles across, far wider than the
  area of the results. No pins were visible in my capture, so I cannot say how
  selection is shared between pins and cards.
- With dates and the Hotels filter on, the page reported "2 properties found"
  and "95% of places to stay are unavailable". Its count depends on room
  availability. Ours is a count of places near a point, and must say so.
- Prices and sorting are tied to paid placement ("How payments affect property
  ranking"), which has no equivalent here.

## What the documentation says

**Geoapify Places** (read 2026-09-29):

- Hotels are the category `accommodation.hotel`.
- A circle around a point is `filter=circle:lon,lat,radiusMeters`. **Longitude
  comes first.**
- `bias=proximity:lon,lat` orders results nearest first and adds a `distance` in
  metres to each result.
- `limit` defaults to 20 (maximum 500). The free plan allows about 3000
  requests a day, and every 20 places costs one credit.
- Results are a GeoJSON collection. Each has a `place_id`, `lat`, `lon`, and
  `formatted` address; many other fields (`name`, `website`, `distance`) are
  optional.

A live request for ZIP 16802 returned a full page of 20 hotels, each with an
id, a name, coordinates, an address, a distance, and an OpenStreetMap
attribution. **The provider returns no prices, ratings, photos, or
availability.**

**Leaflet** (read 2026-09-29): markers can be tabbed to and are activated with
Enter (`keyboard`, on by default), and the map itself takes arrow-key and `+`/`-`
control. A tile layer takes an `attribution` string. Leaflet's default marker
icon is an image that bundlers often fail to find, so a `divIcon` avoids that.

**OpenStreetMap tiles** (read 2026-09-29): no API key is needed, visible
attribution ("© OpenStreetMap contributors") is required and must not be hidden,
bulk downloading is forbidden, and a valid Referer must be sent.

## Decisions

1. **List beside map, on one screen** (Booking.com's layout, not Expedia's
   overlay). On a narrow screen the two stack, the map first, so both stay
   visible without opening anything.
2. **Selecting in either place selects the same hotel in the other.** A hotel is
   identified by its provider `place_id`. Clicking or pressing Enter on a list
   card or a map pin highlights both, and the map recentres on the pin.
3. **Search is around the point the ZIP resolved to.** The summary line states
   that centre and radius, and the map marks the centre separately from the
   hotels, so nobody mistakes it for a hotel.
4. **Only what the provider returned is shown.** A card has a name, an address,
   a distance, and a website when there is one. There are no prices, ratings,
   photos, availability, or "N left" messages. A missing name reads "Name not
   provided"; a missing address or distance is left out.
5. **Every state gets its own message**: loading (skeleton cards), results,
   invalid ZIP (blocked in the browser, no request), a ZIP that is not resolved,
   no hotels within 5 km, a rate-limited service, and a failed request. A
   failure never reads as "no hotels".
6. **The list is honest about its size.** Twenty results is one page. When a
   page is full the summary says "showing the nearest 20 hotels, there may be
   more", and the app never says it lists every hotel.
7. **OpenStreetMap's standard tiles**, with "© OpenStreetMap contributors"
   always visible. This means no tile credential in the browser at all, so the
   backend Geoapify key cannot leak into frontend configuration. The trade-off
   is the tile policy's best-effort service, which is acceptable for local
   classroom use.
8. **Markers are Leaflet `divIcon`s** (numbered, with a text label), which keeps
   them keyboard-focusable and avoids the bundler icon problem.
9. **Keyboard**: the ZIP box submits on Enter, each list card is a real button,
   and map pins take focus and activate on Enter.

## What the research changed

Two decisions come straight from what was observed. Booking.com's skeleton
placeholders are why loading gets its own state that cannot be mistaken for an
empty result. Expedia's list, which mixed in properties 12 to 32 miles away, is
why the summary states the search centre and the 5 km radius, so a traveler can
see what "nearby" means here. The list-and-map layout follows Booking.com; the
separate overlay on Expedia is what to avoid.

## Revisions made while building (added 2026-09-29, after the mockup)

The sections above and the mockup are kept as they were written before the list
and map code. These are the places the finished interface differs, and why.

1. **"Powered by Geoapify" was added.** Reading Geoapify's pricing and terms
   pages during the build showed the free plan requires OpenStreetMap
   attribution and Geoapify's own: a visible "Powered by Geoapify" link. The
   mockup showed only the OpenStreetMap credit on the map. The results section
   now carries both. The same pages said nothing about caching or storing
   results, so Part 2 will keep only what a traveler chooses to save.
2. **The map pans only when it needs to.** The mockup said selecting a hotel
   recentres the map. In use that would move the map on every click of a pin
   that is already in view, so it now pans only when the selected pin is near or
   past the edge. The list scrolls to the selected card in the same way.
3. **Enter and Space are handled on `keydown`.** The mockup said pins activate on
   Enter. Testing with real key presses showed Leaflet answers Enter only
   through the deprecated `keypress` event and never answers Space, so Enter
   did nothing in this browser. Both keys are now handled on `keydown`, as a
   button does.
4. **A backend that is down gets its own message.** The mockup listed "request
   failed" as one state. In development the proxy answers with a bare HTTP 500
   when nothing listens on port 8000, which first showed as "Request failed with
   status 500." It now says the backend could not be reached.
5. **Hotel names are treated as untrusted text.** OpenStreetMap is editable by
   anyone, and Leaflet reads a string tooltip as HTML, so tooltip text is built
   from a text node. A test with a name containing an `<img onerror>` tag showed
   it rendered as plain text in the list, the tooltip, and the pin's label.
6. **The ZIP centre table from the graded in-class activity stays** above the
   results, so the search centre is stated twice: in the table and in the
   summary line.
7. **Markers were drawn in the wrong place.** The first real-size screenshot
   showed the ZIP centre diamond far outside the dashed radius circle it should
   sit in the middle of. The cause was CSS `rotate` and `scale` on the marker
   element: they are applied before Leaflet's own `translate3d`, so they rotated
   and shrank the marker's offset. A selected pin, which scaled up, would have
   drifted the same way. My earlier checks only compared CSS classes, which is
   why they passed. Those effects now sit on an inner element. A geometry check
   confirmed the diamond is 0.3 px from the circle's centre, and that a selected
   pin is centred on its true position at 1.25 times the size.
8. **Selecting a pin no longer scrolls the page.** The list scrolled to the
   chosen card with `scrollIntoView`, which also scrolls the window. When the
   two columns stack, that would drag the map out of view on every pin click. The
   list now scrolls only itself. Measured at 1280 px and 600 px wide: selecting
   the 15th hotel scrolled the list 1702 px and 1432 px, and moved the page and
   the map by 0.
