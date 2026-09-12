/**
 * Backend access layer.
 *
 * Components never call `fetch` directly; they import from here. This module
 * owns URL construction and turns any backend failure into an Error whose
 * message is safe to display.
 */

const BASE_URL = '/api'

async function readErrorMessage(response) {
  let body
  try {
    body = await response.json()
  } catch {
    return `Request failed with status ${response.status}.`
  }

  if (body?.error?.message) {
    return body.error.message
  }

  return `Request failed with status ${response.status}.`
}

/**
 * Search hotels by name. An empty name returns every hotel.
 *
 * @param {string} name Part of a hotel name, matched case-insensitively.
 * @returns {Promise<{query: string, count: number, hotels: Array}>}
 */
export async function searchHotels(name) {
  const query = new URLSearchParams({ name })
  const response = await fetch(`${BASE_URL}/hotels?${query}`)

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  return response.json()
}
