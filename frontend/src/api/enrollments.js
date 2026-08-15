import { apiFetch } from './client'

// `courseId` (optional) narrows results to that course's expected
// current-batch students (by programme + semester-derived enrollment year).
// Pass `backlog: true` alongside it to instead search the whole department
// for students from an *earlier* batch, for "Add Backlog Student".
export const listStudents = (courseId, { backlog = false } = {}) => {
  if (!courseId) return apiFetch('/api/v1/students')
  const params = new URLSearchParams({ course_id: courseId })
  if (backlog) params.set('backlog', 'true')
  return apiFetch(`/api/v1/students?${params}`)
}

export const listEnrollments = (courseId) => apiFetch(`/api/v1/courses/${courseId}/enrollments`)

export const enrollStudents = (courseId, studentIds) =>
  apiFetch(`/api/v1/courses/${courseId}/enrollments`, {
    method: 'POST',
    body: { student_ids: studentIds },
  })

export const unenrollStudent = (courseId, studentId) =>
  apiFetch(`/api/v1/courses/${courseId}/enrollments/${studentId}`, { method: 'DELETE' })

// Enrollment via file upload (PDF/Excel), matched against existing student
// accounts -- see EnrollImportModal. Preview parses/validates only; nothing
// is enrolled until confirm.
export const previewEnrollmentImport = (courseId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch(`/api/v1/courses/${courseId}/enrollments/import/preview`, {
    method: 'POST',
    body: formData,
  })
}

export const confirmEnrollmentImport = (courseId, studentIds) =>
  apiFetch(`/api/v1/courses/${courseId}/enrollments/import/confirm`, {
    method: 'POST',
    body: { student_ids: studentIds },
  })
