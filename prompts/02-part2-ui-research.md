# 02 - Part 2: UI research

**Purpose:** Turn visual preferences from real travel sites into a concrete
design direction before changing the interface.

```
Before changing the interface, research it. Start from the working hotel search
and keep its behaviour. Compare Expedia, Priceline, and Booking.com. Inspect how
Priceline's date field behaves when opened, not just how it looks.

Use Expedia as the base interface: its landscape hero, overlapping search card,
and illustrated category icons. Add Priceline's two-month calendar. Treat
Booking.com's home page as the example to avoid: saturated colour and stacked
promotions competing with the search.

Record the references, what to keep, and what to avoid in docs/ui-research.md,
then redesign to match. Afterwards compare the result with the references and
confirm the original search still works.
```

**Boundaries it set:** the Part 1 search behaviour is preserved; references are
compared before anything is built; one example is chosen as a design to avoid.

**Decisions worth reusing:** dates and traveler counts in the references filter
results, but every stay here has fixed dates, so the calendar is a planning aid
and the page says so. Categories this app does not handle open Expedia in a new
tab rather than pretending to work.

**Verification worth reusing:** after the redesign, repeat the Part 1 searches.
`Harbor Lantern` still returns one hotel with two stays, and `Sunset Palms`
still shows the no-results message.
