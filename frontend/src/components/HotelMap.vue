<script setup>
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  center: { type: Object, required: true },
  radiusM: { type: Number, required: true },
  hotels: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
})

const emit = defineEmits(['select'])

// OpenStreetMap's standard tiles need no key, so no credential reaches the browser.
// Their policy requires this credit to stay visible on the map.
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
const NO_NAME = 'Name not provided'

const mapElement = ref(null)

// Leaflet objects are kept out of Vue's reactivity on purpose.
let map = null
let resizeObserver = null
let drawnLayer = null
const markers = new Map()

function hotelLabel(hotel) {
  return hotel.name || NO_NAME
}

// Hotel names come from OpenStreetMap, which anyone can edit. Leaflet treats a
// string tooltip as HTML, so hand it a text node instead.
function textContent(text) {
  const span = document.createElement('span')
  span.textContent = text
  return span
}

function pinIcon(number) {
  return L.divIcon({
    className: 'hotel-pin',
    html: `<span>${number}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
}

function centreIcon() {
  return L.divIcon({
    className: 'centre-mark',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function drawHotel(hotel, index) {
  const label = hotelLabel(hotel)
  const marker = L.marker([hotel.latitude, hotel.longitude], {
    icon: pinIcon(index + 1),
    title: label,
    keyboard: true,
    riseOnHover: true,
  })

  marker.on('click', () => emit('select', hotel.place_id))
  marker.bindTooltip(textContent(label), { direction: 'top', offset: [0, -14] })
  marker.addTo(drawnLayer)

  // Leaflet marks a keyboard marker as a button, but it only answers Enter through the
  // deprecated keypress event, and never answers Space. Handle both on keydown, as a
  // button does. preventDefault stops Leaflet's own Enter handling from firing twice.
  const element = marker.getElement()
  if (element) {
    element.setAttribute('aria-label', `${index + 1}. ${label}`)
    element.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return
      event.preventDefault()
      emit('select', hotel.place_id)
    })
  }

  markers.set(hotel.place_id, marker)
}

function redraw() {
  if (!map) return

  drawnLayer?.remove()
  markers.clear()
  drawnLayer = L.layerGroup().addTo(map)

  const centre = [props.center.latitude, props.center.longitude]
  const radius = L.circle(centre, {
    radius: props.radiusM,
    color: '#1668e3',
    weight: 2,
    dashArray: '8 6',
    fill: false,
    interactive: false,
  }).addTo(drawnLayer)
  L.marker(centre, {
    icon: centreIcon(),
    interactive: false,
    keyboard: false,
    title: 'ZIP code centre',
  }).addTo(drawnLayer)

  props.hotels.forEach(drawHotel)

  // The whole search radius, so "within 5 km" is visible and no result is cropped.
  map.fitBounds(radius.getBounds(), { padding: [16, 16] })
  applySelection(false)
}

function applySelection(shouldReveal) {
  markers.forEach((marker, placeId) => {
    const isSelected = placeId === props.selectedId
    marker.getElement()?.classList.toggle('selected', isSelected)
    marker.setZIndexOffset(isSelected ? 1000 : 0)
    if (isSelected) marker.openTooltip()
    else marker.closeTooltip()
  })

  const selected = markers.get(props.selectedId)
  if (!shouldReveal || !selected) return

  // Only move the map when the pin is near or past its edge.
  if (!map.getBounds().pad(-0.15).contains(selected.getLatLng())) {
    map.panTo(selected.getLatLng())
  }
}

onMounted(() => {
  map = L.map(mapElement.value)
  L.tileLayer(TILE_URL, { maxZoom: 19, attribution: TILE_ATTRIBUTION }).addTo(map)
  map.setView([props.center.latitude, props.center.longitude], 13)

  redraw()

  // The container can change size (stacked layout, window resize).
  resizeObserver = new ResizeObserver(() => map?.invalidateSize())
  resizeObserver.observe(mapElement.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  map?.remove()
  map = null
})

watch(() => [props.center, props.radiusM, props.hotels], redraw)
watch(() => props.selectedId, () => applySelection(true))
</script>

<template>
  <div class="map-frame">
    <div
      ref="mapElement"
      class="map"
      role="region"
      aria-label="Map of hotels near the ZIP code. Use the arrow keys to move the map and plus and minus to zoom."
    ></div>
    <p class="legend">
      <span class="key"><span class="swatch centre" aria-hidden="true"></span> ZIP code centre</span>
      <span class="key"><span class="swatch radius" aria-hidden="true"></span> 5 km search radius</span>
      <span class="key"><span class="swatch pin" aria-hidden="true"></span> Hotel (numbered as in the list)</span>
    </p>
  </div>
</template>

<style scoped>
.map-frame {
  display: grid;
  gap: 0.5rem;
}

.map {
  height: 32rem;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #e9eef0;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.2rem;
  margin: 0;
  font-size: 0.8rem;
  color: var(--muted);
}

.key {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.swatch {
  display: inline-block;
}

.swatch.centre {
  width: 0.7rem;
  height: 0.7rem;
  background: var(--ink);
  transform: rotate(45deg);
}

.swatch.radius {
  width: 1.2rem;
  border-top: 2px dashed var(--brand);
}

.swatch.pin {
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 50%;
  background: #5a6079;
}

/* Leaflet builds its icons outside Vue's templates, so these must reach in. */
.map :deep(.hotel-pin) {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #5a6079;
  box-shadow: 0 1px 4px rgb(0 0 0 / 35%);
  color: #fff;
  font: 700 13px/1 Arial, Helvetica, sans-serif;
  cursor: pointer;
}

.map :deep(.hotel-pin.selected) {
  background: var(--brand);
  box-shadow:
    0 0 0 4px rgb(22 104 227 / 30%),
    0 1px 4px rgb(0 0 0 / 35%);
  scale: 1.25;
}

.map :deep(.hotel-pin:focus-visible) {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.map :deep(.centre-mark) {
  width: 22px;
  height: 22px;
  border: 2px solid #fff;
  background: var(--ink);
  box-shadow: 0 1px 4px rgb(0 0 0 / 35%);
  rotate: 45deg;
  scale: 0.7;
}

@media (max-width: 760px) {
  .map {
    height: 22rem;
  }
}
</style>
