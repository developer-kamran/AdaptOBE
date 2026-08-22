import { apiBaseUrl, apiFetch, downloadExport, getAccessToken } from './client'

export function getCourseAttainment(courseId) {
  return apiFetch(`/api/v1/attainment/course/${courseId}`)
}

export function recalculateCourseAttainment(courseId) {
  return apiFetch(`/api/v1/attainment/course/${courseId}/recalculate`, { method: 'POST' })
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
