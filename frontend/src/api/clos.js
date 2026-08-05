import { apiFetch } from './client'

export const listClos = (courseId) => apiFetch(`/api/v1/courses/${courseId}/clos`)

export const createClo = (courseId, data) =>
  apiFetch(`/api/v1/courses/${courseId}/clos`, { method: 'POST', body: data })
