import { apiFetch } from './client'

export const listMyCourses = () => apiFetch('/api/v1/courses?mine=true')
export const getCourse = (courseId) => apiFetch(`/api/v1/courses/${courseId}`)
export const createCourse = (data) => apiFetch('/api/v1/courses', { method: 'POST', body: data })
