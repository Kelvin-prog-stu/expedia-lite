<script setup>
import { computed, onMounted, ref } from 'vue'

import {
  cancelBooking,
  createBooking,
  deleteBooking,
  listBookings,
  listUsers,
  lookUpZip,
  searchHotels,
} from '@/api'
import BookingHistory from '@/components/BookingHistory.vue'
import DateRangePicker from '@/components/DateRangePicker.vue'
import SearchResults from '@/components/SearchResults.vue'
import TravelIcon from '@/components/TravelIcon.vue'
import ZipLookupPanel from '@/components/ZipLookupPanel.vue'

// Stays is handled here; every other category opens Expedia in a new tab.
const CATEGORIES = [
  { key: 'stays', label: 'Stays' },
  { key: 'flights', label: 'Flights', href: 'https://www.expedia.com/Flights' },
  { key: 'cars', label: 'Cars', href: 'https://www.expedia.com/Cars' },
  { key: 'packages', label: 'Packages', href: 'https://www.expedia.com/Vacation-Packages' },
  { key: 'activities', label: 'Things to do', href: 'https://www.expedia.com/Activities' },
  { key: 'cruises', label: 'Cruises', href: 'https://www.expedia.com/Cruises' },
]

const nameQuery = ref('')
const validationMessage = ref('')
const checkIn = ref('')
const checkOut = ref('')

const users = ref([])
const selectedUserId = ref('')
const results = ref(null)
const bookings = ref([])

const isSearching = ref(false)
const bookingTripId = ref('')
const busyBookingId = ref('')
const statusMessage = ref('')
const errorMessage = ref('')

// Five digits, as a string: 00501 is a real ZIP and must keep its leading zeros.
const ZIP_PATTERN = /^\d{5}$/

const zipQuery = ref('')
const zipLocation = ref(null)
const zipErrorMessage = ref('')
const zipValidationMessage = ref('')
const isLookingUpZip = ref(false)

const travelerName = computed(
  () => users.value.find((u) => u.user_id === selectedUserId.value)?.display_name ?? '',
)

function announce(message) {
  errorMessage.value = ''
  statusMessage.value = message
}

function fail(error) {
  statusMessage.value = ''
  errorMessage.value = error.message
}

async function refreshBookings() {
  if (!selectedUserId.value) return
  try {
    bookings.value = await listBookings(selectedUserId.value)
  } catch (error) {
    fail(error)
  }
}

async function runSearch(query) {
  const name = query.trim()
  if (!name) {
    validationMessage.value = 'Enter a hotel name.'
    return
  }

  validationMessage.value = ''
  isSearching.value = true
  try {
    results.value = await searchHotels(name)
  } catch (error) {
    fail(error)
  } finally {
    isSearching.value = false
  }
}

function onSearch() {
  runSearch(nameQuery.value)
}

function exploreSuggestion() {
  nameQuery.value = 'Valley Trail'
  runSearch(nameQuery.value)
}

async function onBook(row) {
  bookingTripId.value = row.trip_id
  try {
    const booking = await createBooking(selectedUserId.value, row.trip_id)
    await refreshBookings()
    announce(
      `Booked ${booking.booking_id}: ${booking.trip_name} at ${booking.hotel_name} for ${booking.display_name}.`,
    )
  } catch (error) {
    fail(error)
  } finally {
    bookingTripId.value = ''
  }
}

async function onCancel(bookingId) {
  busyBookingId.value = bookingId
  try {
    await cancelBooking(bookingId)
    await refreshBookings()
    announce(`Cancelled ${bookingId}. It stays in your history.`)
  } catch (error) {
    fail(error)
  } finally {
    busyBookingId.value = ''
  }
}

async function onDelete(bookingId) {
  busyBookingId.value = bookingId
  try {
    await deleteBooking(bookingId)
    await refreshBookings()
    announce(`Deleted ${bookingId}.`)
  } catch (error) {
    fail(error)
  } finally {
    busyBookingId.value = ''
  }
}

async function onLookUpZip() {
  // Clear the earlier answer first, so a stale location is never read as the new one.
  zipLocation.value = null
  zipErrorMessage.value = ''
  zipValidationMessage.value = ''

  const zipCode = zipQuery.value.trim()
  if (!zipCode) {
    zipValidationMessage.value = 'Enter a ZIP code.'
    return
  }
  if (!ZIP_PATTERN.test(zipCode)) {
    zipValidationMessage.value = 'A ZIP code is five digits, for example 16802.'
    return
  }

  isLookingUpZip.value = true
  try {
    zipLocation.value = await lookUpZip(zipCode)
  } catch (error) {
    zipErrorMessage.value = error.message
  } finally {
    isLookingUpZip.value = false
  }
}

async function onTravelerChange() {
  statusMessage.value = ''
  await refreshBookings()
}

onMounted(async () => {
  try {
    users.value = await listUsers()
    selectedUserId.value = users.value[0]?.user_id ?? ''
    await refreshBookings()
  } catch (error) {
    fail(error)
  }
})
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="#search" aria-label="Expedia Lite home">
        <span class="brand-mark" aria-hidden="true">
          <TravelIcon name="flights" :size="22" />
        </span>
        <span class="brand-text">Expedia <span>Lite</span></span>
      </a>
      <nav class="topnav" aria-label="Main">
        <a href="#search">Find a stay</a>
        <a href="#bookings">My bookings</a>
        <a href="https://www.expedia.com/" target="_blank" rel="noopener noreferrer">
          Explore Expedia <TravelIcon name="external" :size="13" />
        </a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="hero-eyebrow">Stays for the season</p>
        <h1 id="hero-title">Find the stay that fits the trip.</h1>
        <p class="hero-sub">Search hotels, book an offered stay, and keep track of every trip.</p>
      </div>
    </section>

    <section id="search" class="search-card" aria-label="Search stays">
      <nav class="categories" aria-label="Travel categories">
        <template v-for="category in CATEGORIES" :key="category.key">
          <span v-if="!category.href" class="category active" aria-current="page">
            <TravelIcon :name="category.key" />
            <span>{{ category.label }}</span>
          </span>
          <a
            v-else
            class="category"
            :href="category.href"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`${category.label} on Expedia, opens in a new tab`"
          >
            <TravelIcon :name="category.key" />
            <span>
              {{ category.label }}
              <TravelIcon name="external" :size="11" class="outbound" />
            </span>
          </a>
        </template>
      </nav>

      <form class="search-row" novalidate @submit.prevent="onSearch">
        <label class="field field-hotel">
          <span class="field-label">Hotel name</span>
          <input
            v-model="nameQuery"
            type="search"
            placeholder="Where would you like to stay?"
            autocomplete="off"
            :aria-invalid="Boolean(validationMessage)"
            aria-describedby="search-help"
          />
        </label>

        <div class="field-slot">
          <DateRangePicker v-model:check-in="checkIn" v-model:check-out="checkOut" />
        </div>

        <label class="field field-traveler">
          <span class="field-label">Booking as</span>
          <select v-model="selectedUserId" @change="onTravelerChange">
            <option v-for="user in users" :key="user.user_id" :value="user.user_id">
              {{ user.display_name }}
            </option>
          </select>
        </label>

        <button type="submit" class="search-button" :disabled="isSearching">
          {{ isSearching ? 'Searching...' : 'Search' }}
        </button>
      </form>

      <div id="search-help" class="search-help">
        <span>Search by a full or partial hotel name.</span>
        <span>Dates are for planning and don't filter results.</span>
      </div>
      <p v-if="validationMessage" class="validation" role="alert">{{ validationMessage }}</p>
    </section>

    <section class="promo" aria-label="Suggested stay">
      <span class="promo-icon"><TravelIcon name="stays" :size="40" /></span>
      <div class="promo-copy">
        <h2>A quiet weekend in the hills.</h2>
        <p>Start with Valley Trail Inn in State College, Pennsylvania.</p>
      </div>
      <button type="button" class="promo-button" @click="exploreSuggestion">
        Explore this stay &rarr;
      </button>
    </section>

    <div class="status" aria-live="polite">
      <p v-if="statusMessage" class="toast success">{{ statusMessage }}</p>
      <p v-if="errorMessage" class="toast error" role="alert">{{ errorMessage }}</p>
    </div>

    <div class="content">
      <SearchResults
        v-if="results"
        :results="results"
        :traveler-name="travelerName"
        :booking-trip-id="bookingTripId"
        @book="onBook"
      />
      <section v-else class="placeholder">
        <TravelIcon name="stays" :size="40" />
        <p><strong>Somewhere good is a search away.</strong></p>
        <p>Enter a hotel name above to see its stays and nightly rates.</p>
      </section>

      <BookingHistory
        :bookings="bookings"
        :traveler-name="travelerName"
        :busy-id="busyBookingId"
        @cancel="onCancel"
        @delete="onDelete"
      />

      <ZipLookupPanel
        v-model="zipQuery"
        :location="zipLocation"
        :is-loading="isLookingUpZip"
        :error-message="zipErrorMessage"
        :validation-message="zipValidationMessage"
        @submit="onLookUpZip"
      />
    </div>
  </main>

  <footer class="footer">
    <span>Expedia Lite</span>
    <span>Classroom project &middot; Fictional hotels &middot; Simulated bookings</span>
  </footer>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid var(--line);
  background: #fff;
}

.topbar-inner,
.content,
.footer {
  width: min(72rem, calc(100% - 2.5rem));
  margin: 0 auto;
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8rem 0;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--ink);
  text-decoration: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 8px;
  background: var(--promo);
}

.brand-text {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.brand-text span {
  font-weight: 500;
  color: var(--muted);
}

.topnav {
  display: flex;
  flex-wrap: wrap;
  gap: 1.4rem;
}

.topnav a {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--ink);
  font-weight: 600;
  text-decoration: none;
}

.topnav a:hover {
  color: var(--brand);
}

.hero {
  padding: 4.5rem 1.25rem 7.5rem;
  background:
    linear-gradient(180deg, rgb(12 22 48 / 5%) 0%, rgb(12 22 48 / 35%) 100%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 420' preserveAspectRatio='xMidYMid slice'%3E%3Cdefs%3E%3ClinearGradient id='s' x1='0' y1='0' x2='0' y2='1'%3E%3Cstop offset='0' stop-color='%23a9c4e6'/%3E%3Cstop offset='1' stop-color='%23f3d9b8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1440' height='420' fill='url(%23s)'/%3E%3Ccircle cx='1120' cy='120' r='46' fill='%23fff3d6'/%3E%3Cpath d='M0 300 L180 170 L330 260 L520 120 L700 250 L880 150 L1060 240 L1250 140 L1440 230 V420 H0Z' fill='%237d8fb3'/%3E%3Cpath d='M0 340 L220 230 L420 320 L640 210 L860 310 L1080 220 L1300 300 L1440 260 V420 H0Z' fill='%235b6e96'/%3E%3Cpath d='M0 380 L260 300 L520 370 L780 290 L1040 360 L1300 300 L1440 340 V420 H0Z' fill='%233c4f78'/%3E%3C/svg%3E")
      center / cover;
  color: #fff;
  text-align: center;
}

.hero-eyebrow {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0.5rem 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 500;
  text-shadow: 0 2px 16px rgb(12 22 48 / 35%);
}

.hero-sub {
  margin: 0;
  font-size: 1.05rem;
}

.search-card {
  position: relative;
  width: min(66rem, calc(100% - 2.5rem));
  margin: -5.5rem auto 0;
  padding: 0 1.5rem 1.2rem;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 18px 50px rgb(25 30 59 / 18%);
}

.categories {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.25rem;
  border-bottom: 1px solid var(--line);
}

.category {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
  min-width: 6.5rem;
  padding: 1rem 0.6rem 0.8rem;
  border-bottom: 3px solid transparent;
  color: var(--ink);
  font-size: 0.92rem;
  font-weight: 600;
  text-decoration: none;
}

a.category:hover {
  background: var(--surface);
}

.category.active {
  border-bottom-color: var(--brand);
  color: var(--brand);
}

.outbound {
  vertical-align: -1px;
  opacity: 0.6;
}

.search-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr auto;
  gap: 0.75rem;
  margin-top: 1.2rem;
}

.field {
  display: grid;
  gap: 0.15rem;
  padding: 0.55rem 0.9rem;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
}

.field:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgb(22 104 227 / 18%);
}

.field-label {
  font-size: 0.75rem;
  color: var(--muted);
}

.field input,
.field select {
  width: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  font: inherit;
  font-size: 1rem;
  color: var(--ink);
  outline: none;
}

.field-hotel {
  padding-left: 2.6rem;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23191e3b' stroke-width='2'%3E%3Cpath d='M12 21s-7-6.2-7-11.5A7 7 0 0112 2.5a7 7 0 017 7C19 14.8 12 21 12 21z'/%3E%3Ccircle cx='12' cy='9.5' r='2.5'/%3E%3C/svg%3E") no-repeat 0.85rem center / 1.15rem;
}

.search-button {
  padding: 0 2rem;
  border: 0;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-size: 1.05rem;
  font-weight: 700;
  cursor: pointer;
}

.search-button:hover:not(:disabled) {
  background: var(--brand-dark);
}

.search-button:disabled {
  background: #aab4c8;
}

.search-button:focus-visible,
.promo-button:focus-visible,
a:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.search-help {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.7rem;
  font-size: 0.82rem;
  color: var(--muted);
}

.validation {
  margin: 0.5rem 0 0;
  color: #b3261e;
  font-weight: 600;
}

.promo {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1.1rem;
  width: min(66rem, calc(100% - 2.5rem));
  margin: 2rem auto 0;
  padding: 1.3rem 1.6rem;
  border-radius: 16px;
  background: var(--promo);
}

.promo-icon {
  display: grid;
  place-items: center;
  width: 3.8rem;
  height: 3.8rem;
  border-radius: 50%;
  background: #fff;
}

.promo-copy {
  flex: 1 1 18rem;
}

.promo-copy h2 {
  margin: 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.6rem;
  font-weight: 500;
}

.promo-copy p {
  margin: 0.2rem 0 0;
}

.promo-button {
  padding: 0.75rem 1.4rem;
  border: 0;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.status {
  width: min(66rem, calc(100% - 2.5rem));
  margin: 1.2rem auto 0;
}

.toast {
  margin: 0;
  padding: 0.85rem 1.1rem;
  border-radius: 10px;
  font-weight: 600;
}

.success {
  border-left: 4px solid #1d8a4c;
  background: #e3f4ea;
  color: #155e34;
}

.error {
  border-left: 4px solid #b3261e;
  background: #fbeceb;
  color: #8a1f18;
}

.content {
  display: grid;
  /* minmax(0, 1fr) stops a wide table from stretching the whole column. */
  grid-template-columns: minmax(0, 1fr);
  gap: 3rem;
  padding: 2.5rem 0 3rem;
}

.placeholder {
  display: grid;
  justify-items: center;
  gap: 0.2rem;
  padding: 2.5rem 1rem;
  border: 1px dashed var(--line-strong);
  border-radius: 14px;
  color: var(--muted);
  text-align: center;
}

.placeholder p {
  margin: 0;
}

.placeholder strong {
  color: var(--ink);
}

.footer {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 1.5rem 0 2.5rem;
  border-top: 1px solid var(--line);
  font-size: 0.85rem;
  color: var(--muted);
}

@media (max-width: 760px) {
  .search-row {
    grid-template-columns: 1fr;
  }

  .search-button {
    padding: 0.85rem;
  }

  .topnav {
    gap: 0.9rem;
    font-size: 0.9rem;
  }
}
</style>
