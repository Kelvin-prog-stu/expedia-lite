<script setup>
defineProps({
  location: { type: Object, default: null },
  isLoading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

defineEmits(['look-up'])
</script>

<template>
  <section class="zip-demo" aria-labelledby="zip-demo-title">
    <p class="eyebrow">Location data</p>
    <h2 id="zip-demo-title">ZIP lookup demonstration</h2>
    <p class="summary">
      One fixed ZIP code, resolved by the backend through a public location service. The
      service key stays on the server; the browser only receives the location.
    </p>

    <button type="button" class="zip-button" :disabled="isLoading" @click="$emit('look-up')">
      {{ isLoading ? 'Looking up...' : 'Look up ZIP 16802' }}
    </button>

    <p v-if="isLoading" class="pending" role="status">Asking the location service...</p>

    <dl v-else-if="location" class="result">
      <div class="pair">
        <dt>ZIP code</dt>
        <dd>{{ location.postcode }}</dd>
      </div>
      <div v-if="location.locality" class="pair">
        <dt>Locality</dt>
        <dd>{{ location.locality }}</dd>
      </div>
      <div class="pair">
        <dt>Country</dt>
        <dd>{{ location.country_code }}</dd>
      </div>
      <div class="pair">
        <dt>Latitude</dt>
        <dd>{{ location.latitude }}</dd>
      </div>
      <div class="pair">
        <dt>Longitude</dt>
        <dd>{{ location.longitude }}</dd>
      </div>
    </dl>

    <p v-else-if="errorMessage" class="failed" role="alert">{{ errorMessage }}</p>
  </section>
</template>

<style scoped>
.zip-demo {
  padding: 1.5rem 1.6rem 1.7rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface);
}

.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

h2 {
  margin: 0.15rem 0 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.5rem;
  font-weight: 500;
}

.summary {
  margin: 0.35rem 0 1rem;
  max-width: 44rem;
  color: var(--muted);
}

.zip-button {
  padding: 0.7rem 1.4rem;
  border: 0;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
}

.zip-button:hover:not(:disabled) {
  background: var(--brand);
}

.zip-button:disabled {
  background: #aab4c8;
  cursor: progress;
}

.zip-button:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.pending {
  margin: 1rem 0 0;
  color: var(--muted);
}

.result {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 2.5rem;
  margin: 1.1rem 0 0;
  padding: 1rem 1.2rem;
  border-radius: 12px;
  background: #fff;
}

.pair dt {
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}

.pair dd {
  margin: 0.15rem 0 0;
  font-size: 1.05rem;
  font-weight: 700;
}

.failed {
  margin: 1.1rem 0 0;
  padding: 0.85rem 1.1rem;
  border-left: 4px solid #b3261e;
  border-radius: 10px;
  background: #fbeceb;
  color: #8a1f18;
  font-weight: 600;
}
</style>
