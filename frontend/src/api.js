/**
 * Backend access layer.
 *
 * Components never call `fetch` directly; they import from here. This module
 * owns URL construction and turns any backend failure into an Error whose
 * message is safe to display.
 */

const BASE_URL = '/api'

const BACKEND_UNREACHABLE =
  'The app could not get an answer from its backend. Check that it is running, then try again.'

/**
 * A failed request. `code` is the backend's error code ("location_not_found",
 * "rate_limited", ...) so a caller can tell kinds of failure apart without
 * reading the message. It is "network" when the backend could not be reached.
 */
export class ApiError extends Error {
  constructor(message, code = 'unknown', status = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

async function readError(response) {
  try {
    const body = await response.json()
    if (body?.error?.message) {
      return new ApiError(body.error.message, body.error.code, response.status)
    }
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      return new ApiError(body.detail[0].msg, 'validation', response.status)
    }
  } catch {
    // Not JSON: fall through to the generic messages below.
  }
  // A server error with no error body did not come from our backend's own handlers. In
  // development that is the Vite proxy answering because nothing is listening on port 8000.
  if (response.status >= 500) return new ApiError(BACKEND_UNREACHABLE, 'network', response.status)
  return new ApiError(`Request failed with status ${response.status}.`, 'unknown', response.status)
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    // fetch only throws when nothing answered at all.
    throw new ApiError(BACKEND_UNREACHABLE, 'network')
  }

  if (!response.ok) {
    throw await readError(response)
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

/**
 * Hotels within 5 km of the point a five digit US ZIP code resolves to.
 *
 * The backend holds the provider's API key and makes both outside requests, so
 * nothing about the provider appears in this file. The ZIP stays a string, so
 * leading zeros survive. An empty `hotels` list is a successful search.
 */
export function findNearbyHotels(zipCode) {
  return request(`/nearby-hotels?${new URLSearchParams({ zip: zipCode })}`)
}
