import { apiFetch } from './client'

export function listAttendance(courseId) {
  return apiFetch(`/api/v1/courses/${courseId}/attendance`)
}

export function setAttendance(courseId, entries) {
  return apiFetch(`/api/v1/courses/${courseId}/attendance`, {
    method: 'POST',
    body: { entries },
  })
}
