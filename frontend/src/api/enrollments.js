import { apiFetch } from './client'

export const listStudents = () => apiFetch('/api/v1/students')

export const listEnrollments = (courseId) => apiFetch(`/api/v1/courses/${courseId}/enrollments`)

export const enrollStudents = (courseId, studentIds) =>
  apiFetch(`/api/v1/courses/${courseId}/enrollments`, {
    method: 'POST',
    body: { student_ids: studentIds },
  })

export const unenrollStudent = (courseId, studentId) =>
  apiFetch(`/api/v1/courses/${courseId}/enrollments/${studentId}`, { method: 'DELETE' })
