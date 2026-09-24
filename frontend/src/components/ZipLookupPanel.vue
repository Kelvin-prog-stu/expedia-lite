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

    <div v-else-if="location" class="table-wrap">
      <table>
        <caption class="visually-hidden">Location returned for the ZIP code entered</caption>
        <thead>
          <tr>
            <th scope="col">ZIP code</th>
            <th scope="col">Locality</th>
            <th scope="col">Country</th>
            <th scope="col">Latitude</th>
            <th scope="col">Longitude</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="zip">{{ location.postcode }}</td>
            <td>{{ location.locality || 'Not provided' }}</td>
            <td>{{ location.country_code }}</td>
            <td>{{ location.latitude }}</td>
            <td>{{ location.longitude }}</td>
          </tr>
        </tbody>
      </table>
    </div>

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

.table-wrap {
  /* Contains the absolutely positioned visually-hidden caption, which would
     otherwise escape this scroll container and widen the whole page. */
  position: relative;
  overflow-x: auto;
  margin: 1.1rem 0 0;
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

tbody td {
  border-bottom: 0;
}

.zip {
  font-weight: 700;
  letter-spacing: 0.06em;
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
