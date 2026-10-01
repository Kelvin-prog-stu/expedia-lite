<script setup>
import { computed } from 'vue'

import HotelList from '@/components/HotelList.vue'
import HotelMap from '@/components/HotelMap.vue'

const props = defineProps({
  nearby: { type: Object, default: null },
  isLoading: { type: Boolean, default: false },
  selectedId: { type: String, default: '' },
  savedIds: { type: Array, default: () => [] },
  pendingIds: { type: Array, default: () => [] },
  // { kind: 'success' | 'error', text } for the last save, removal, or live search.
  feedback: { type: Object, default: null },
  isShowingLive: { type: Boolean, default: false },
})

defineEmits(['select', 'add', 'remove', 'show-live'])

const isLocal = computed(() => props.nearby?.source === 'local')
const radiusKm = computed(() => (props.nearby ? props.nearby.radius_m / 1000 : 0))

const place = computed(() => {
  if (!props.nearby) return ''
  const { locality, postcode } = props.nearby.location
  return locality ? `${locality} ${postcode}` : `ZIP ${postcode}`
})

const heading = computed(() => {
  if (props.isLoading) return 'Finding hotels...'
  if (!props.nearby) return ''
  return isLocal.value ? `Saved hotels near ${place.value}` : `Hotels near ${place.value}`
})

const centreText = computed(() => {
  if (!props.nearby) return ''
  const { latitude, longitude } = props.nearby.location
  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
})

const count = computed(() => props.nearby?.hotels.length ?? 0)
</script>

<template>
  <section
    v-if="isLoading || nearby"
    id="nearby"
    class="nearby"
    aria-labelledby="nearby-title"
    :aria-busy="isLoading"
  >
    <p class="eyebrow">
      Nearby hotels
      <span
        v-if="nearby && !isLoading"
        class="source"
        :class="isLocal ? 'local' : 'api'"
        data-testid="source-label"
      >
        {{ isLocal ? 'Saved locally' : 'API results' }}
      </span>
    </p>
    <h2 id="nearby-title">{{ heading }}</h2>

    <div v-if="isLoading" class="layout" aria-hidden="true">
      <div class="skeleton-list">
        <span v-for="n in 4" :key="n" class="skeleton-card"></span>
      </div>
      <div class="skeleton-map"></div>
    </div>

    <template v-else>
      <p class="summary" role="status">
        <template v-if="isLocal">
          <template v-if="count > 0">
            {{ count }} {{ count === 1 ? 'hotel' : 'hotels' }} saved for {{ place }} (centre
            {{ centreText }}, {{ radiusKm }} km search).
            <strong>These are only the hotels saved for this ZIP, not every hotel in the area.</strong>
          </template>
          <template v-else>No saved hotels remain for {{ place }}.</template>
        </template>
        <template v-else-if="count > 0">
          {{ count }} {{ count === 1 ? 'hotel' : 'hotels' }} within {{ radiusKm }} km of
          {{ place }} (centre {{ centreText }}), nearest first.
          <strong v-if="nearby.may_have_more">
            Showing the nearest {{ nearby.limit }}; there may be more.
          </strong>
        </template>
        <template v-else>No hotels found within {{ radiusKm }} km of {{ place }}.</template>
      </p>

      <p v-if="isLocal" class="live-row">
        <button type="button" class="live-button" :disabled="isShowingLive" @click="$emit('show-live')">
          {{ isShowingLive ? 'Loading live results...' : 'Show live API results for this ZIP' }}
        </button>
      </p>

      <p
        v-if="feedback"
        class="feedback"
        :class="feedback.kind"
        :role="feedback.kind === 'error' ? 'alert' : 'status'"
      >
        {{ feedback.text }}
      </p>

      <p v-if="nearby.omitted_count > 0" class="note">
        {{ nearby.omitted_count }}
        {{ nearby.omitted_count === 1 ? 'result was' : 'results were' }} left out because the
        service gave no usable location for {{ nearby.omitted_count === 1 ? 'it' : 'them' }}.
      </p>

      <div class="layout">
        <div class="list-column">
          <HotelList
            v-if="count > 0"
            :hotels="nearby.hotels"
            :selected-id="selectedId"
            :saved-ids="savedIds"
            :pending-ids="pendingIds"
            @select="$emit('select', $event)"
            @add="$emit('add', $event)"
            @remove="$emit('remove', $event)"
          />
          <p v-else-if="isLocal" class="empty">
            Nothing is saved for this ZIP now. Search the ZIP again to see live API results.
          </p>
          <p v-else class="empty">
            The location service lists no hotels within {{ radiusKm }} km of this point. That does
            not prove there are none. Try another ZIP code.
          </p>
        </div>

        <div class="map-column">
          <HotelMap
            :center="nearby.location"
            :radius-m="nearby.radius_m"
            :hotels="nearby.hotels"
            :selected-id="selectedId"
            @select="$emit('select', $event)"
          />
        </div>
      </div>

      <p class="fine-print">
        <template v-if="isLocal">
          Saved locally: places you saved from the location service, with simulated classroom
          rates and rooms. The rates and rooms are not from the hotel API, which has no prices or
          availability.
        </template>
        <template v-else>
          These are places the location service lists as hotels: names, addresses, and coordinates
          only. It has no prices, ratings, or availability, and a page of {{ nearby.limit }} is not
          a complete list of hotels.
        </template>
        <span class="credit">
          Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Geoapify</a><template v-if="nearby.attribution">. Hotel data {{ nearby.attribution }}</template>.
        </span>
      </p>
    </template>
  </section>
</template>

<style scoped>
.eyebrow {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.source {
  padding: 0.15rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  /* The heading above is uppercase; these two labels are meant to read as written. */
  letter-spacing: 0;
  text-transform: none;
}

.source.local {
  background: #e3f4ea;
  color: #155e34;
}

.source.api {
  background: #e4edfc;
  color: #1550a8;
}

h2 {
  margin: 0.15rem 0 0.4rem;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.75rem;
  font-weight: 500;
}

.summary {
  margin: 0 0 0.6rem;
  color: var(--ink);
}

.note {
  margin: 0 0 0.6rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.live-row {
  margin: 0 0 0.6rem;
}

.live-button {
  padding: 0.4rem 1rem;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: #fff;
  color: var(--brand);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
}

.live-button:hover:not(:disabled) {
  background: var(--brand);
  color: #fff;
}

.live-button:disabled {
  border-color: var(--line-strong);
  color: var(--muted);
  cursor: progress;
}

.live-button:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.feedback {
  margin: 0 0 0.7rem;
  padding: 0.7rem 1rem;
  border-radius: 10px;
  font-weight: 600;
}

.feedback.success {
  border-left: 4px solid #1d8a4c;
  background: #e3f4ea;
  color: #155e34;
}

.feedback.error {
  border-left: 4px solid #b3261e;
  background: #fbeceb;
  color: #8a1f18;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 26rem) minmax(0, 1fr);
  gap: 1.25rem;
  margin-top: 0.8rem;
}

.empty {
  margin: 0;
  padding: 1rem 1.2rem;
  border-left: 4px solid var(--promo);
  border-radius: 8px;
  background: #fff8e1;
  color: #6b5313;
  font-weight: 600;
}

.fine-print {
  margin: 1rem 0 0;
  font-size: 0.82rem;
  color: var(--muted);
}

.credit a {
  color: var(--brand);
  font-weight: 600;
}

.skeleton-list {
  display: grid;
  gap: 0.6rem;
}

.skeleton-card,
.skeleton-map {
  display: block;
  border-radius: 12px;
  background: linear-gradient(90deg, #e6e9f2 25%, #f1f3f9 50%, #e6e9f2 75%) 0 0 / 200% 100%;
  animation: shimmer 1.4s linear infinite;
}

.skeleton-card {
  height: 5.2rem;
}

.skeleton-map {
  height: 32rem;
}

@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-card,
  .skeleton-map {
    animation: none;
  }
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  /* Map first, so both stay on the page when the columns stack. */
  .map-column {
    order: -1;
  }

  .skeleton-map {
    height: 22rem;
  }
}
</style>
