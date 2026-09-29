<script setup>
import { computed } from 'vue'

import HotelList from '@/components/HotelList.vue'
import HotelMap from '@/components/HotelMap.vue'

const props = defineProps({
  nearby: { type: Object, default: null },
  isLoading: { type: Boolean, default: false },
  selectedId: { type: String, default: '' },
})

defineEmits(['select'])

const radiusKm = computed(() => (props.nearby ? props.nearby.radius_m / 1000 : 0))

const place = computed(() => {
  if (!props.nearby) return ''
  const { locality, postcode } = props.nearby.location
  return locality ? `${locality} ${postcode}` : `ZIP ${postcode}`
})

const heading = computed(() => {
  if (props.isLoading) return 'Finding hotels...'
  return props.nearby ? `Hotels near ${place.value}` : ''
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
    <p class="eyebrow">Nearby hotels</p>
    <h2 id="nearby-title">{{ heading }}</h2>

    <div v-if="isLoading" class="layout" aria-hidden="true">
      <div class="skeleton-list">
        <span v-for="n in 4" :key="n" class="skeleton-card"></span>
      </div>
      <div class="skeleton-map"></div>
    </div>

    <template v-else>
      <p class="summary" role="status">
        <template v-if="count > 0">
          {{ count }} {{ count === 1 ? 'hotel' : 'hotels' }} within {{ radiusKm }} km of
          {{ place }} (centre {{ centreText }}), nearest first.
          <strong v-if="nearby.may_have_more">
            Showing the nearest {{ nearby.limit }}; there may be more.
          </strong>
        </template>
        <template v-else>No hotels found within {{ radiusKm }} km of {{ place }}.</template>
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
            @select="$emit('select', $event)"
          />
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
        These are places the location service lists as hotels: names, addresses, and coordinates
        only. It has no prices, ratings, or availability, and a page of {{ nearby.limit }} is not a
        complete list of hotels.
        <span class="credit">
          Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Geoapify</a><template v-if="nearby.attribution">. Hotel data {{ nearby.attribution }}</template>.
        </span>
      </p>
    </template>
  </section>
</template>

<style scoped>
.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
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

.layout {
  display: grid;
  grid-template-columns: minmax(0, 24rem) minmax(0, 1fr);
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
