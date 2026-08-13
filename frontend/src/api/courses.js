import { apiFetch } from './client'

export const listMyCourses = () => apiFetch('/api/v1/courses?mine=true')
export const listDepartmentCourses = () => apiFetch('/api/v1/courses')
export const getCourse = (courseId) => apiFetch(`/api/v1/courses/${courseId}`)
export const createCourse = (data) => apiFetch('/api/v1/courses', { method: 'POST', body: data })
export const updateCourse = (courseId, data) =>
  apiFetch(`/api/v1/courses/${courseId}`, { method: 'PATCH', body: data })
export const deleteCourse = (courseId) =>
  apiFetch(`/api/v1/courses/${courseId}`, { method: 'DELETE' })
