# UI research

How the Part 2 interface was chosen, following the In-class Activity 2 method:
start from the working app, compare real travel sites, record what to keep and
what to avoid, then turn that evidence into a design direction.

## 1. Starting point

The Part 1 app searched hotels by name and showed the results in a plain table.
It worked: searching `Harbor Lantern` returned Harbor Lantern Hotel with both of
its stays, and `Sunset Palms` showed a no-results message. Whatever the redesign
does, that search has to keep working exactly as before.

## 2. References compared

Three booking sites, side by side: **Expedia**, **Priceline**, and
**Booking.com**. Each puts search at the top of the page, but they differ a lot
in how much else competes for attention.

## 3. An interaction, not just a look

Priceline's date field opens a calendar showing **two months side by side**,
with the check-in and check-out range highlighted and a Done button. Seeing a
whole month and the next one at once makes it easy to pick a stay that crosses
the month boundary, which several of our stays do (for example Boston Autumn
Weekend, 2026-10-02 to 2026-10-04, sits right after a September stay at the same
hotel).

## 4. What to keep

- **Expedia's page structure.** A landscape hero, a white search card that
  overlaps it, and a row of **illustrated category icons** (Stays, Flights, Cars,
  Packages, Things to do, Cruises) above the search fields. The icons make the
  categories readable at a glance.
- **Priceline's two-month calendar**, described above.
- **Expedia's grouped search row.** Destination, dates, and travelers sit in one
  row of labelled fields with a single Search button at the end.

## 5. What surrounds the search

Below the search, Expedia uses one bright promotional banner and then hotel
cards with the name, location, and price given equal weight. That suggests a
single highlighted suggestion rather than a wall of offers, and results that
lead with the hotel name and the nightly rate.

## 6. What to avoid

**Booking.com's home page** is the contrasting example. The saturated blue hero,
the stack of promotional cards competing for attention, and the crowded search
bar make it hard to tell what the page is for. The redesign keeps promotional
content to one banner and keeps colour mostly neutral so the search and the
results stay the focus.

## 7. Design direction

Use **Expedia as the base**: hero, overlapping search card, illustrated category
icons, one promotional banner. Add **Priceline's two-month calendar** for the
date field. Keep the **existing hotel-name search** unchanged in behaviour.

Two adjustments for this app specifically:

- **Dates and travelers are planning aids, not filters.** Every stay here has
  fixed dates, so the calendar and traveler count do not narrow the results, and
  the page says so under the search row rather than leaving it to be discovered.
- **Categories other than Stays open Expedia in a new tab**, marked with an
  outgoing-link icon, since this app only handles hotel stays.

Part 2 also needs booking and history, which none of the references were chosen
for. Those follow the same visual language: each offered stay gets a Book
button, and booking history sits in its own section below the results with
clear status labels and Cancel and Delete actions.

## Checking the result

After building, compare the interface against the choices above: Expedia layout
and icons present, two-month calendar working, Booking.com-style clutter absent.
Then repeat the original Part 1 search to confirm it still behaves the same.
