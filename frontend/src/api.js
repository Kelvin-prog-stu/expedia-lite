/**
 * Backend access layer.
 *
 * Components never call `fetch` directly; they import from here. This module
 * owns URL construction and turns any backend failure into an Error whose
 * message is safe to display.
 */

const BASE_URL = '/api'

async function readErrorMessage(response) {
  try {
    const body = await response.json()
    if (body?.error?.message) return body.error.message
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    // Fall through to the generic message below.
  }
  return `Request failed with status ${response.status}.`
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  return response.status === 204 ? null : response.json()
}

/** Search hotels by name. An empty name returns every hotel. */
export function searchHotels(name) {
  return request(`/hotels?${new URLSearchParams({ name })}`)
}

/** The demo travelers who can make bookings. */
export function listUsers() {
  return request('/users')
}

/** Read: booking history, for one traveler when userId is given. */
export function listBookings(userId) {
  const query = userId ? `?${new URLSearchParams({ user_id: userId })}` : ''
  return request(`/bookings${query}`)
}

/** Create: book an offered stay for a traveler. */
export function createBooking(userId, tripId) {
  return request('/bookings', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, trip_id: tripId }),
  })
}

/** Update: cancel a booking while keeping the record. */
export function cancelBooking(bookingId) {
  return request(`/bookings/${encodeURIComponent(bookingId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'cancelled' }),
  })
}

/** Delete: remove a booking permanently. */
export function deleteBooking(bookingId) {
  return request(`/bookings/${encodeURIComponent(bookingId)}`, { method: 'DELETE' })
}
