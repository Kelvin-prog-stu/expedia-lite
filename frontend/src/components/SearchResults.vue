<script setup>
import { computed } from 'vue'

import TravelIcon from './TravelIcon.vue'

const props = defineProps({
  results: { type: Object, required: true },
  travelerName: { type: String, default: '' },
  bookingTripId: { type: String, default: '' },
})

const emit = defineEmits(['book'])

/** One row per offered stay, since each stay is what gets booked. */
const rows = computed(() =>
  props.results.hotels.flatMap((hotel) =>
    hotel.trips.map((trip) => ({ ...trip, hotel })),
  ),
)

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

function formatDate(iso) {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}
</script>

<template>
  <section class="results" aria-live="polite" aria-labelledby="results-title">
    <p class="eyebrow">Your next getaway</p>
    <h2 id="results-title">Stays for your search</h2>

    <p v-if="results.count === 0" class="empty">
      No hotels match "{{ results.query }}". Try another hotel name.
    </p>

    <template v-else>
      <p class="summary">
        {{ results.count }} hotel<span v-if="results.count !== 1">s</span>
        found<span v-if="results.query"> for "{{ results.query }}"</span>,
        {{ rows.length }} stay<span v-if="rows.length !== 1">s</span> offered.
      </p>

      <div class="table-wrap">
        <table>
          <caption class="visually-hidden">Hotels and their offered stays</caption>
          <thead>
            <tr>
              <th scope="col">Hotel</th>
              <th scope="col">Location</th>
              <th scope="col">Hotel ID</th>
              <th scope="col">Stay</th>
              <th scope="col">Dates</th>
              <th scope="col" class="numeric">Nightly rate</th>
              <th scope="col"><span class="visually-hidden">Book</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.trip_id">
              <td>
                <span class="hotel">
                  <span class="hotel-icon"><TravelIcon name="stays" :size="26" /></span>
                  {{ row.hotel.hotel_name }}
                </span>
              </td>
              <td>{{ row.hotel.city }}, {{ row.hotel.state }}</td>
              <td class="muted">{{ row.hotel.hotel_id }}</td>
              <td>{{ row.trip_name }}</td>
              <td class="dates">{{ formatDate(row.check_in) }} - {{ formatDate(row.check_out) }}</td>
              <td class="numeric">
                <strong>{{ money.format(row.hotel.nightly_rate_usd) }}</strong>
                <span class="per-night">per night</span>
              </td>
              <td class="action">
                <button
                  type="button"
                  class="book"
                  :disabled="!travelerName || bookingTripId === row.trip_id"
                  :aria-label="`Book ${row.trip_name} at ${row.hotel.hotel_name}`"
                  @click="emit('book', row)"
                >
                  {{ bookingTripId === row.trip_id ? 'Booking...' : 'Book' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}

h2 {
  margin: 0.2rem 0 0.4rem;
  font-size: 1.75rem;
}

.summary {
  margin: 0 0 1rem;
  color: var(--muted);
}

.empty {
  padding: 1rem 1.2rem;
  border-left: 4px solid var(--promo);
  border-radius: 8px;
  background: #fff8e1;
  color: #6b5313;
  font-weight: 600;
}

.table-wrap {
  /* Contains the absolutely positioned visually-hidden labels, which would
     otherwise escape this scroll container and widen the whole page. */
  position: relative;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

th,
td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}

thead th {
  background: var(--surface);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
}

tbody tr:last-child td {
  border-bottom: 0;
}

.hotel {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  font-weight: 700;
}

.hotel-icon {
  display: inline-grid;
  place-items: center;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 8px;
  background: #eef2fb;
}

.muted {
  color: var(--muted);
}

.dates {
  white-space: nowrap;
}

.numeric {
  text-align: right;
  white-space: nowrap;
}

.numeric strong {
  display: block;
  font-size: 1.05rem;
}

.per-night {
  font-size: 0.75rem;
  color: var(--muted);
}

.action {
  text-align: right;
}

.book {
  padding: 0.5rem 1.1rem;
  border: 0;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.book:hover:not(:disabled) {
  background: var(--brand-dark);
}

.book:disabled {
  background: #aab4c8;
  cursor: not-allowed;
}

.book:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
</style>
