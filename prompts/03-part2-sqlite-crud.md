# 03 - Part 2: SQLite CRUD with MVC

**Purpose:** Move storage to SQLite and add booking, history, cancel, and delete,
structured as Model, View, and Controller.

```
Seed a SQLite database with the supplied hotel, trip, user, and booking records.
After seeding, all reads and writes use SQLite. Starting the app again must
preserve saved changes without duplicating or reloading the starter records.
Preserve existing IDs and assign unique IDs to new records.

Implement CRUD using Model-View-Controller: models hold the data and
relationships, the view presents the interface, and a database controller
performs the create, read, update, and delete operations.

Through the frontend: create a booking, read it in history, cancel it by updating
its status while keeping the record, and delete a test booking. Develop on a
feature branch and merge into main after checking.
```

**Boundaries it set:** no SQL outside the controller; the controller imports
nothing from FastAPI; cancellation never deletes.

**Decisions worth reusing:** seeding is recorded with a marker in an `app_meta`
table rather than inferred from row counts, so deleting every booking can never
trigger a reseed. The next booking number is stored there too, so an ID is never
reused after a deletion: delete `B008` and the next booking is `B009`.

**Verification worth reusing:** record the table counts, restart both servers,
and compare. Counts that stay at 8 hotels, 12 trips, and 6 users prove seeding
did not run twice; a cancelled booking still showing as cancelled proves the
update persisted.
