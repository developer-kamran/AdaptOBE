import { apiFetch } from './client'

export const suggestMappings = (cloId, limit = 3) =>
  apiFetch('/api/v1/mappings/suggest', { method: 'POST', body: { clo_id: cloId, limit } })

export const confirmMapping = (data) =>
  apiFetch('/api/v1/mappings/confirm', { method: 'POST', body: data })

export const listMappingsForClo = (cloId) => apiFetch(`/api/v1/mappings/clo/${cloId}`)

export const deleteMapping = (mappingId) =>
  apiFetch(`/api/v1/mappings/${mappingId}`, { method: 'DELETE' })
