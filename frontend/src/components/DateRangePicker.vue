<script setup>
import { computed, nextTick, ref } from 'vue'

// Two months side by side, after Priceline's date picker. Dates are a planning
// aid only: every stay in this app has fixed dates, so they never filter results.
const checkIn = defineModel('checkIn', { type: String, default: '' })
const checkOut = defineModel('checkOut', { type: String, default: '' })

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const FIRST_MONTH = new Date(2026, 8, 1) // September 2026, when the supplied stays begin

const isOpen = ref(false)
const monthOffset = ref(0)
const dialog = ref(null)

function isoDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function buildMonth(offset) {
  const first = new Date(FIRST_MONTH.getFullYear(), FIRST_MONTH.getMonth() + offset, 1)
  const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate()
  const cells = Array.from({ length: first.getDay() }, () => null)
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(isoDate(new Date(first.getFullYear(), first.getMonth(), day)))
  }
  return {
    key: isoDate(first),
    label: first.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
    cells,
  }
}

const months = computed(() => [buildMonth(monthOffset.value), buildMonth(monthOffset.value + 1)])

function formatShort(iso) {
  if (!iso) return ''
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

const summary = computed(() => {
  if (checkIn.value && checkOut.value) {
    return `${formatShort(checkIn.value)} - ${formatShort(checkOut.value)}`
  }
  if (checkIn.value) return `${formatShort(checkIn.value)} - Add check-out`
  return 'Add dates'
})

function selectDay(iso) {
  if (!checkIn.value || checkOut.value || iso <= checkIn.value) {
    checkIn.value = iso
    checkOut.value = ''
    return
  }
  checkOut.value = iso
}

function dayState(iso) {
  if (iso === checkIn.value || iso === checkOut.value) return 'selected'
  if (checkIn.value && checkOut.value && iso > checkIn.value && iso < checkOut.value) {
    return 'in-range'
  }
  return ''
}

async function open() {
  isOpen.value = true
  await nextTick()
  dialog.value?.focus()
}

function close() {
  isOpen.value = false
}

function clearDates() {
  checkIn.value = ''
  checkOut.value = ''
}
</script>

<template>
  <button type="button" class="field-button" aria-haspopup="dialog" @click="open">
    <span class="field-label">Dates</span>
    <span class="field-value">{{ summary }}</span>
  </button>

  <div v-if="isOpen" class="backdrop" @click.self="close" @keydown.esc="close">
    <div
      ref="dialog"
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="calendar-title"
      tabindex="-1"
    >
      <header class="dialog-head">
        <div>
          <h2 id="calendar-title">When's your getaway?</h2>
          <p>Choose check-in and check-out dates for planning.</p>
        </div>
        <button type="button" class="icon-button" aria-label="Close calendar" @click="close">
          &times;
        </button>
      </header>

      <div class="months">
        <button
          type="button"
          class="nav prev"
          aria-label="Previous month"
          :disabled="monthOffset === 0"
          @click="monthOffset -= 1"
        >
          &lsaquo;
        </button>

        <div v-for="month in months" :key="month.key" class="month">
          <h3>{{ month.label }}</h3>
          <div class="grid" role="grid" :aria-label="month.label">
            <span v-for="weekday in WEEKDAYS" :key="weekday" class="weekday">{{ weekday }}</span>
            <template v-for="(iso, index) in month.cells" :key="iso ?? `blank-${index}`">
              <span v-if="!iso" class="blank" />
              <button
                v-else
                type="button"
                class="day"
                :class="dayState(iso)"
                :aria-pressed="dayState(iso) === 'selected'"
                @click="selectDay(iso)"
              >
                {{ Number(iso.slice(8)) }}
              </button>
            </template>
          </div>
        </div>

        <button type="button" class="nav next" aria-label="Next month" @click="monthOffset += 1">
          &rsaquo;
        </button>
      </div>

      <footer class="dialog-foot">
        <span class="range">
          {{ checkIn ? formatShort(checkIn) : 'Check-in' }} -
          {{ checkOut ? formatShort(checkOut) : 'Check-out' }}
        </span>
        <button type="button" class="text-button" @click="clearDates">Clear dates</button>
        <button type="button" class="done" @click="close">Done</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.field-button {
  display: grid;
  gap: 0.15rem;
  width: 100%;
  height: 100%;
  padding: 0.55rem 0.9rem 0.55rem 2.6rem;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: #fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23191e3b' stroke-width='2'%3E%3Crect x='3' y='5' width='18' height='16' rx='2'/%3E%3Cpath d='M3 10h18M8 3v4M16 3v4'/%3E%3C/svg%3E") no-repeat 0.85rem center / 1.1rem;
  text-align: left;
  cursor: pointer;
}

.field-label {
  font-size: 0.75rem;
  color: var(--muted);
}

.field-value {
  font-size: 1rem;
  color: var(--ink);
}

.backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(25 30 59 / 45%);
  backdrop-filter: blur(3px);
}

.dialog {
  width: min(44rem, 100%);
  max-height: calc(100vh - 2rem);
  overflow: auto;
  padding: 1.4rem 1.5rem 1.1rem;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 24px 60px rgb(25 30 59 / 30%);
}

.dialog:focus {
  outline: none;
}

.dialog-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-head h2 {
  margin: 0;
  font-size: 1.35rem;
}

.dialog-head p {
  margin: 0.25rem 0 0;
  color: var(--muted);
}

.icon-button {
  width: 2.2rem;
  height: 2.2rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
}

.icon-button:hover {
  background: var(--surface);
}

.months {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 1.5rem;
  margin: 1.2rem 0 1rem;
  padding: 0 1.2rem;
}

.nav {
  position: absolute;
  top: -0.2rem;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--brand);
  font-size: 1.6rem;
  cursor: pointer;
}

.nav:disabled {
  color: var(--line-strong);
  cursor: default;
}

.prev {
  left: -0.4rem;
}

.next {
  right: -0.4rem;
}

.month h3 {
  margin: 0 0 0.7rem;
  font-size: 1rem;
  text-align: center;
}

.grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.2rem;
}

.weekday {
  padding-bottom: 0.3rem;
  font-size: 0.72rem;
  color: var(--muted);
  text-align: center;
}

.day {
  aspect-ratio: 1;
  border: 0;
  border-radius: 50%;
  background: transparent;
  font-size: 0.9rem;
  color: var(--ink);
  cursor: pointer;
}

.day:hover {
  background: var(--surface);
}

.day.in-range {
  border-radius: 0;
  background: #e4ecfb;
}

.day.selected {
  background: var(--brand);
  color: #fff;
  font-weight: 700;
}

.dialog-foot {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--line);
}

.range {
  margin-right: auto;
  font-weight: 600;
}

.text-button {
  border: 0;
  background: transparent;
  color: var(--brand);
  font-weight: 600;
  cursor: pointer;
}

.done {
  padding: 0.6rem 1.5rem;
  border: 0;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

:where(button):focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
</style>
