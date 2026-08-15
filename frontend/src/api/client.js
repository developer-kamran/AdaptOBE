const BASE_URL = import.meta.env.VITE_API_BASE_URL

const ACCESS_TOKEN_KEY = 'adaptobe.access_token'
const REFRESH_TOKEN_KEY = 'adaptobe.refresh_token'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem(ACCESS_TOKEN_KEY, access_token)
  if (refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function parseError(response) {
  try {
    const body = await response.json()
    return body.detail || response.statusText
  } catch {
    return response.statusText
  }
}

// Refresh-on-401 is coalesced into a single in-flight request, so N concurrent
// calls that all 401 at once trigger one refresh, not N races against the
// same (now consumed) refresh token.
let refreshPromise = null

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) return false

      const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        clearTokens()
        return false
      }

      const body = await response.json()
      setTokens({ access_token: body.access_token })
      return true
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

/**
 * @param {string} path - API path, e.g. "/api/v1/courses"
 * @param {object} [options]
 * @param {string} [options.method]
 * @param {object} [options.body]
 * @param {boolean} [options.skipAuth]
 * @param {boolean} [options.raw] - return the Response instead of parsed JSON (for file downloads)
 */
export async function apiFetch(path, { method = 'GET', body, skipAuth = false, raw = false } = {}) {
  // File uploads must go up as multipart. The browser has to set
  // Content-Type itself so it can include the multipart boundary, so we
  // neither set the header nor JSON-stringify in that case.
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  const doFetch = () => {
    const headers = isFormData ? {} : { 'Content-Type': 'application/json' }
    if (!skipAuth) {
      const token = getAccessToken()
      if (token) headers.Authorization = `Bearer ${token}`
    }
    return fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let response = await doFetch()

  if (response.status === 401 && !skipAuth && getRefreshToken()) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      response = await doFetch()
    }
  }

  if (!response.ok) {
    const detail = await parseError(response)
    throw new ApiError(detail, response.status, detail)
  }

  if (raw) return response
  if (response.status === 204) return null
  return response.json()
}

export function apiBaseUrl() {
  return BASE_URL
}
