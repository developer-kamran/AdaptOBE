import { apiFetch } from './client'

export const listClos = (courseId) => apiFetch(`/api/v1/courses/${courseId}/clos`)

export const createClo = (courseId, data) =>
  apiFetch(`/api/v1/courses/${courseId}/clos`, { method: 'POST', body: data })

export const updateClo = (cloId, data) =>
  apiFetch(`/api/v1/clos/${cloId}`, { method: 'PATCH', body: data })

export const deleteClo = (cloId) => apiFetch(`/api/v1/clos/${cloId}`, { method: 'DELETE' })

export const generateCloSuggestion = (courseId, data) =>
  apiFetch(`/api/v1/courses/${courseId}/clos/generate`, { method: 'POST', body: data })
