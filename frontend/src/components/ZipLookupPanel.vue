<script setup>
const zipCode = defineModel({ type: String, default: '' })

defineProps({
  location: { type: Object, default: null },
  isLoading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  validationMessage: { type: String, default: '' },
})

defineEmits(['submit'])
</script>

<template>
  <section class="zip-lookup" aria-labelledby="zip-lookup-title">
    <p class="eyebrow">Location data</p>
    <h2 id="zip-lookup-title">Where are you headed?</h2>
    <p class="summary">
      Enter a United States ZIP code. The backend resolves it through a public location
      service, so the service key stays on the server and the browser only receives the
      location.
    </p>

    <form class="zip-form" novalidate @submit.prevent="$emit('submit')">
      <label class="field">
        <span class="field-label">ZIP code</span>
        <input
          v-model="zipCode"
          type="text"
          inputmode="numeric"
          maxlength="5"
          placeholder="16802"
          autocomplete="postal-code"
          :aria-invalid="Boolean(validationMessage)"
          aria-describedby="zip-help"
        />
      </label>

      <button type="submit" class="zip-button" :disabled="isLoading">
        {{ isLoading ? 'Looking up...' : 'Find location' }}
      </button>
    </form>

    <p id="zip-help" class="zip-help">Five digits, including any leading zeros.</p>

    <p v-if="validationMessage" class="invalid" role="alert">{{ validationMessage }}</p>

    <p v-else-if="isLoading" class="pending" role="status">Asking the location service...</p>

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
.zip-lookup {
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

.zip-form {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.75rem;
}

.field {
  display: grid;
  gap: 0.15rem;
  padding: 0.55rem 0.9rem;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: #fff;
}

.field:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgb(22 104 227 / 18%);
}

.field-label {
  font-size: 0.75rem;
  color: var(--muted);
}

.field input {
  width: 7ch;
  border: 0;
  padding: 0;
  background: transparent;
  font: inherit;
  font-size: 1.05rem;
  letter-spacing: 0.08em;
  color: var(--ink);
  outline: none;
}

.zip-button {
  padding: 0 1.6rem;
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

.zip-help {
  margin: 0.6rem 0 0;
  font-size: 0.82rem;
  color: var(--muted);
}

.invalid {
  margin: 0.6rem 0 0;
  color: #b3261e;
  font-weight: 600;
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
