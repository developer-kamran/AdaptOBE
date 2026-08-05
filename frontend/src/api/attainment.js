import { apiBaseUrl, apiFetch, getAccessToken } from './client'

export function getCourseAttainment(courseId) {
  return apiFetch(`/api/v1/attainment/course/${courseId}`)
}

export function recalculateCourseAttainment(courseId) {
  return apiFetch(`/api/v1/attainment/course/${courseId}/recalculate`, { method: 'POST' })
}

async function downloadExport(path, filenameFallback) {
  const response = await apiFetch(path, { raw: true })
  const blob = await response.blob()

  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="([^"]+)"/)
  const filename = match ? match[1] : filenameFallback

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function exportCoursePdf(courseId) {
  return downloadExport(`/api/v1/attainment/course/${courseId}/export/pdf`, 'attainment.pdf')
}

export function exportCourseExcel(courseId) {
  return downloadExport(`/api/v1/attainment/course/${courseId}/export/excel`, 'attainment.xlsx')
}

/** ws:// / wss:// URL for the live-updates socket, carrying the access token as a query param
 * since the browser WebSocket API cannot set an Authorization header. */
export function courseWebSocketUrl(courseId) {
  const wsBase = apiBaseUrl().replace(/^http/, 'ws')
  return `${wsBase}/api/v1/ws/course/${courseId}?token=${encodeURIComponent(getAccessToken() ?? '')}`
}
