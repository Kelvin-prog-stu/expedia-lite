<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  hotels: { type: Array, required: true },
  selectedId: { type: String, default: '' },
  // Provider ids the database says are saved, and ids with a save or removal in flight.
  savedIds: { type: Array, default: () => [] },
  pendingIds: { type: Array, default: () => [] },
})

defineEmits(['select', 'add', 'remove'])

const NO_NAME = 'Name not provided'
const EDGE_GAP_PX = 8

const listElement = ref(null)

// The card elements, by place id. Plain on purpose: nothing renders from it.
const cards = {}

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

function distanceText(metres) {
  if (metres == null) return ''
  if (metres < 1000) return `${metres} m from the ZIP code centre`
  return `${(metres / 1000).toFixed(1)} km from the ZIP code centre`
}

function nightText(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const isSaved = (hotel) => props.savedIds.includes(hotel.place_id)
const isPending = (hotel) => props.pendingIds.includes(hotel.place_id)
const nameOf = (hotel) => hotel.name || NO_NAME

// A pin chosen on the map may sit outside the list's scroll area. Scroll the list itself.
// scrollIntoView would also scroll the page, which drags the map out of sight when the
// two columns stack.
watch(
  () => props.selectedId,
  async (placeId) => {
    const list = listElement.value
    if (!placeId || !list) return
    await nextTick()

    const card = cards[placeId]
    if (!card) return

    const cardBottom = card.offsetTop + card.offsetHeight
    if (card.offsetTop < list.scrollTop) {
      list.scrollTop = card.offsetTop - EDGE_GAP_PX
    } else if (cardBottom > list.scrollTop + list.clientHeight) {
      list.scrollTop = cardBottom - list.clientHeight + EDGE_GAP_PX
    }
  },
)
</script>

<template>
  <ol ref="listElement" class="hotel-list" aria-label="Hotels near the ZIP code, nearest first">
    <li
      v-for="(hotel, index) in hotels"
      :key="hotel.place_id"
      :ref="(element) => (cards[hotel.place_id] = element)"
      class="card"
      :class="{ selected: hotel.place_id === selectedId }"
    >
      <button
        type="button"
        class="pick"
        :aria-pressed="hotel.place_id === selectedId"
        @click="$emit('select', hotel.place_id)"
      >
        <span class="badge" aria-hidden="true">{{ index + 1 }}</span>
        <span class="details">
          <span class="name" :class="{ missing: !hotel.name }">
            <span class="visually-hidden">{{ index + 1 }}. </span>{{ nameOf(hotel) }}
          </span>
          <span v-if="hotel.address" class="line">{{ hotel.address }}</span>
          <span v-if="hotel.distance_m != null" class="line">{{ distanceText(hotel.distance_m) }}</span>
        </span>
      </button>

      <details v-if="hotel.nights" class="nights" open>
        <summary>Simulated classroom rates and rooms</summary>
        <p class="simulated">
          Simulated classroom data. Not rates or availability from the hotel API.
        </p>
        <table>
          <caption class="visually-hidden">
            Simulated nightly rate and rooms available for {{ nameOf(hotel) }}
          </caption>
          <thead>
            <tr>
              <th scope="col">Night</th>
              <th scope="col">Rate</th>
              <th scope="col">Rooms available</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="night in hotel.nights" :key="night.stay_date">
              <td>{{ nightText(night.stay_date) }}</td>
              <td>{{ money.format(night.nightly_rate_cents / 100) }}</td>
              <td>{{ night.rooms_available }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <div class="actions">
        <a
          v-if="hotel.website"
          class="website"
          :href="hotel.website"
          target="_blank"
          rel="noopener noreferrer"
        >
          Website<span class="visually-hidden"> for {{ nameOf(hotel) }}, opens in a new tab</span>
        </a>

        <span v-if="isSaved(hotel)" class="saved-chip">Saved locally</span>

        <button
          type="button"
          class="action add"
          :disabled="isSaved(hotel) || isPending(hotel)"
          :aria-label="`Add ${nameOf(hotel)} to local`"
          @click="$emit('add', hotel)"
        >
          {{ isPending(hotel) && !isSaved(hotel) ? 'Adding...' : 'Add to Local' }}
        </button>

        <button
          v-if="isSaved(hotel)"
          type="button"
          class="action remove"
          :disabled="isPending(hotel)"
          :aria-label="`Remove ${nameOf(hotel)} from local`"
          @click="$emit('remove', hotel)"
        >
          {{ isPending(hotel) ? 'Removing...' : 'Remove from Local' }}
        </button>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.hotel-list {
  /* Makes each card's offsetTop relative to the list, which the scrolling above uses. */
  position: relative;
  display: grid;
  gap: 0.6rem;
  max-height: 32rem;
  margin: 0;
  padding: 0.1rem 0.25rem 0.1rem 0.1rem;
  overflow-y: auto;
  list-style: none;
}

.card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
}

.card.selected {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px var(--brand);
}

.pick {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  width: 100%;
  padding: 0.8rem 0.9rem;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.pick:hover {
  background: var(--surface);
}

.pick:focus-visible,
.website:focus-visible,
.action:focus-visible,
.nights summary:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.badge {
  display: grid;
  flex: none;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 50%;
  background: #5a6079;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 700;
}

.card.selected .badge {
  background: var(--brand);
}

.details {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.name {
  font-weight: 700;
  overflow-wrap: anywhere;
}

.name.missing {
  font-weight: 600;
  font-style: italic;
  color: var(--muted);
}

.line {
  font-size: 0.85rem;
  color: var(--muted);
  overflow-wrap: anywhere;
}

.nights {
  margin: 0 0.9rem 0.6rem 3.6rem;
  padding: 0.5rem 0.7rem 0.6rem;
  border-radius: 10px;
  background: #fff8e1;
  font-size: 0.85rem;
}

.nights summary {
  cursor: pointer;
  font-weight: 700;
  color: #6b5313;
}

.simulated {
  margin: 0.3rem 0 0.4rem;
  color: #6b5313;
}

.nights table {
  width: 100%;
  border-collapse: collapse;
}

.nights th,
.nights td {
  padding: 0.25rem 0.4rem;
  border-bottom: 1px solid #efe2b6;
  text-align: left;
}

.nights th {
  font-size: 0.75rem;
  color: #6b5313;
}

.nights tbody tr:last-child td {
  border-bottom: 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin: 0 0.9rem 0.8rem 3.6rem;
}

.website {
  color: var(--brand);
  font-size: 0.85rem;
  font-weight: 600;
}

.saved-chip {
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background: #e3f4ea;
  color: #155e34;
  font-size: 0.78rem;
  font-weight: 700;
}

.action {
  padding: 0.35rem 0.9rem;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: #fff;
  color: var(--brand);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

.action:hover:not(:disabled) {
  background: var(--brand);
  color: #fff;
}

.action.remove {
  border-color: #b3261e;
  color: #b3261e;
}

.action.remove:hover:not(:disabled) {
  background: #b3261e;
  color: #fff;
}

.action:disabled {
  border-color: var(--line-strong);
  color: var(--muted);
  cursor: not-allowed;
}
</style>
