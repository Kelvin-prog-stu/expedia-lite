<script setup>
import { nextTick, watch } from 'vue'

const props = defineProps({
  hotels: { type: Array, required: true },
  selectedId: { type: String, default: '' },
})

defineEmits(['select'])

const NO_NAME = 'Name not provided'

// The card elements, by place id. Plain on purpose: nothing renders from it.
const cards = {}

function distanceText(metres) {
  if (metres == null) return ''
  if (metres < 1000) return `${metres} m from the ZIP code centre`
  return `${(metres / 1000).toFixed(1)} km from the ZIP code centre`
}

// A pin chosen on the map may sit outside the list's scroll area.
watch(
  () => props.selectedId,
  async (placeId) => {
    if (!placeId) return
    await nextTick()
    cards[placeId]?.scrollIntoView({ block: 'nearest' })
  },
)
</script>

<template>
  <ol class="hotel-list" aria-label="Hotels near the ZIP code, nearest first">
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
            <span class="visually-hidden">{{ index + 1 }}. </span>{{ hotel.name || NO_NAME }}
          </span>
          <span v-if="hotel.address" class="line">{{ hotel.address }}</span>
          <span v-if="hotel.distance_m != null" class="line">{{ distanceText(hotel.distance_m) }}</span>
        </span>
      </button>
      <a
        v-if="hotel.website"
        class="website"
        :href="hotel.website"
        target="_blank"
        rel="noopener noreferrer"
      >
        Website<span class="visually-hidden"> for {{ hotel.name || NO_NAME }}, opens in a new tab</span>
      </a>
    </li>
  </ol>
</template>

<style scoped>
.hotel-list {
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
.website:focus-visible {
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

.website {
  display: inline-block;
  margin: 0 0.9rem 0.8rem 3.6rem;
  color: var(--brand);
  font-size: 0.85rem;
  font-weight: 600;
}
</style>
