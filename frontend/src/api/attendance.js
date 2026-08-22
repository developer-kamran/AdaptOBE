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

export function previewAttendanceImport(courseId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch(`/api/v1/courses/${courseId}/attendance/import/preview`, {
    method: 'POST',
    body: formData,
  })
}

export function confirmAttendanceImport(courseId, entries) {
  return apiFetch(`/api/v1/courses/${courseId}/attendance/import/confirm`, {
    method: 'POST',
    body: { entries },
  })
}
