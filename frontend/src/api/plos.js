import { apiFetch } from './client'

export const listPlos = (programId) =>
  apiFetch(`/api/v1/admin/plos${programId ? `?program_id=${programId}` : ''}`)

export const createPlo = (data) => apiFetch('/api/v1/admin/plos', { method: 'POST', body: data })

export const updatePlo = (ploId, data) =>
  apiFetch(`/api/v1/admin/plos/${ploId}`, { method: 'PATCH', body: data })

export const deletePlo = (ploId) => apiFetch(`/api/v1/admin/plos/${ploId}`, { method: 'DELETE' })
