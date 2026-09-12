<script setup>
import { ref } from 'vue'

import { searchHotels } from '@/api'

const nameQuery = ref('')
const results = ref(null)
const errorMessage = ref('')
const isSearching = ref(false)

async function onSearch() {
  isSearching.value = true
  errorMessage.value = ''

  try {
    results.value = await searchHotels(nameQuery.value)
  } catch (error) {
    results.value = null
    errorMessage.value = error.message
  } finally {
    isSearching.value = false
  }
}

/** Flattens hotels and their stays into one row per offered stay. */
function rowsFor(hotels) {
  return hotels.flatMap((hotel) =>
    hotel.trips.map((trip) => ({
      key: trip.trip_id,
      hotel_name: hotel.hotel_name,
      city: hotel.city,
      state: hotel.state,
      nightly_rate_usd: hotel.nightly_rate_usd,
      trip_name: trip.trip_name,
      check_in: trip.check_in,
      check_out: trip.check_out,
    })),
  )
}
</script>

<template>
  <main class="page">
    <h1>Expedia Lite</h1>
    <p class="subtitle">Search hotels and see the stays offered at each one.</p>

    <form class="search" @submit.prevent="onSearch">
      <label for="hotel-name">Hotel name</label>
      <input
        id="hotel-name"
        v-model="nameQuery"
        type="search"
        placeholder="Harbor Lantern"
        autocomplete="off"
      />
      <button type="submit" :disabled="isSearching">
        {{ isSearching ? 'Searching...' : 'Search' }}
      </button>
    </form>

    <p v-if="errorMessage" class="notice error" role="alert">{{ errorMessage }}</p>

    <section v-if="results" aria-live="polite">
      <p v-if="results.count === 0" class="notice empty">
        No hotels match "{{ results.query }}". Try another hotel name.
      </p>

      <template v-else>
        <p class="summary">
          {{ results.count }} hotel<span v-if="results.count !== 1">s</span> matched.
        </p>

        <table>
          <caption class="visually-hidden">Hotels and their offered stays</caption>
          <thead>
            <tr>
              <th scope="col">Hotel</th>
              <th scope="col">City</th>
              <th scope="col">State</th>
              <th scope="col">Nightly rate (USD)</th>
              <th scope="col">Stay</th>
              <th scope="col">Check in</th>
              <th scope="col">Check out</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rowsFor(results.hotels)" :key="row.key">
              <td>{{ row.hotel_name }}</td>
              <td>{{ row.city }}</td>
              <td>{{ row.state }}</td>
              <td>{{ row.nightly_rate_usd }}</td>
              <td>{{ row.trip_name }}</td>
              <td>{{ row.check_in }}</td>
              <td>{{ row.check_out }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </section>
  </main>
</template>

<style scoped>
.page {
  max-width: 60rem;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}

h1 {
  margin: 0;
  font-size: 1.7rem;
}

.subtitle {
  margin: 0.3rem 0 1.75rem;
  color: #5b6470;
}

.search {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.6rem;
  margin-bottom: 1.5rem;
}

.search label {
  width: 100%;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #5b6470;
}

.search input {
  flex: 1 1 18rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid #b9c0c9;
  border-radius: 4px;
  font-size: 1rem;
}

.search button {
  padding: 0.55rem 1.3rem;
  border: 1px solid #1f3d2b;
  border-radius: 4px;
  background: #2c5a3f;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.search button:hover:not(:disabled) {
  background: #244b34;
}

.search button:disabled {
  background: #9aa5a0;
  border-color: #9aa5a0;
  cursor: not-allowed;
}

:where(input, button):focus-visible {
  outline: 2px solid #8a6a1f;
  outline-offset: 2px;
}

.summary {
  margin: 0 0 0.6rem;
  color: #5b6470;
}

.notice {
  padding: 0.8rem 1rem;
  border-radius: 4px;
  font-weight: 600;
}

.empty {
  border-left: 4px solid #8a6a1f;
  background: #fdf6e6;
  color: #6b5313;
}

.error {
  border-left: 4px solid #a3402f;
  background: #fbeeeb;
  color: #7d2f22;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

th,
td {
  padding: 0.55rem 0.6rem;
  border-bottom: 1px solid #dfe3e8;
  text-align: left;
}

thead th {
  border-bottom: 2px solid #b9c0c9;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #414a55;
}

tbody tr:nth-child(even) {
  background: #f7f9fb;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
