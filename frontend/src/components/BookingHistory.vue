<script setup>
import { ref } from 'vue'

defineProps({
  bookings: { type: Array, required: true },
  travelerName: { type: String, default: '' },
  busyId: { type: String, default: '' },
})

const emit = defineEmits(['cancel', 'delete'])

// Deleting is permanent, so it takes two clicks: Delete, then Confirm delete.
const confirmingId = ref('')

function requestDelete(bookingId) {
  confirmingId.value = bookingId
}

function confirmDelete(bookingId) {
  confirmingId.value = ''
  emit('delete', bookingId)
}

function formatDate(iso) {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
</script>

<template>
  <section id="bookings" class="history" aria-labelledby="history-title">
    <p class="eyebrow">Your trips</p>
    <h2 id="history-title">Booking history</h2>
    <p class="summary">
      <template v-if="travelerName">Bookings for {{ travelerName }}.</template>
      Cancelled bookings stay here for your records.
    </p>

    <p v-if="bookings.length === 0" class="empty">
      No bookings yet for {{ travelerName }}. Search for a hotel and choose Book.
    </p>

    <div v-else class="table-wrap">
      <table>
        <caption class="visually-hidden">Booking history</caption>
        <thead>
          <tr>
            <th scope="col">Booking</th>
            <th scope="col">Hotel</th>
            <th scope="col">Stay</th>
            <th scope="col">Dates</th>
            <th scope="col">Booked on</th>
            <th scope="col">Status</th>
            <th scope="col"><span class="visually-hidden">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="booking in bookings" :key="booking.booking_id" :data-booking="booking.booking_id">
            <td class="mono">{{ booking.booking_id }}</td>
            <td>
              <strong>{{ booking.hotel_name }}</strong>
              <span class="sub">{{ booking.city }}, {{ booking.state }}</span>
            </td>
            <td>{{ booking.trip_name }}</td>
            <td class="nowrap">{{ booking.check_in }} to {{ booking.check_out }}</td>
            <td class="nowrap">{{ formatDate(booking.booked_on) }}</td>
            <td>
              <span class="badge" :class="booking.status">{{ booking.status }}</span>
            </td>
            <td class="actions">
              <button
                v-if="booking.status === 'confirmed'"
                type="button"
                class="secondary"
                :disabled="busyId === booking.booking_id"
                :aria-label="`Cancel booking ${booking.booking_id}`"
                @click="emit('cancel', booking.booking_id)"
              >
                Cancel
              </button>

              <template v-if="confirmingId === booking.booking_id">
                <button
                  type="button"
                  class="danger"
                  :aria-label="`Confirm delete of booking ${booking.booking_id}`"
                  @click="confirmDelete(booking.booking_id)"
                >
                  Confirm delete
                </button>
                <button type="button" class="link" @click="confirmingId = ''">Keep</button>
              </template>
              <button
                v-else
                type="button"
                class="link danger-text"
                :disabled="busyId === booking.booking_id"
                :aria-label="`Delete booking ${booking.booking_id}`"
                @click="requestDelete(booking.booking_id)"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
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
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
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
  padding: 0.8rem 1rem;
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

.mono {
  font-family: ui-monospace, Consolas, monospace;
  font-weight: 700;
}

.sub {
  display: block;
  font-size: 0.8rem;
  color: var(--muted);
}

.nowrap {
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: capitalize;
}

.badge.confirmed {
  background: #e3f4ea;
  color: #1d6b3d;
}

.badge.cancelled {
  background: #f1f2f5;
  color: #5b6272;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  white-space: nowrap;
}

button {
  padding: 0.45rem 0.95rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

button:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.secondary {
  border: 1px solid var(--line-strong);
  background: #fff;
  color: var(--ink);
}

.secondary:hover:not(:disabled) {
  background: var(--surface);
}

.danger {
  border: 0;
  background: #c0392b;
  color: #fff;
}

.link {
  border: 0;
  background: transparent;
  color: var(--brand);
}

.danger-text {
  color: #b3261e;
}
</style>
