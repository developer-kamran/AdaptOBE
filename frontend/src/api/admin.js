import { apiFetch } from './client'

// Departments
export const listDepartments = () => apiFetch('/api/v1/admin/departments')
export const createDepartment = (data) =>
  apiFetch('/api/v1/admin/departments', { method: 'POST', body: data })

// Programs
export const listPrograms = () => apiFetch('/api/v1/admin/programs')
export const createProgram = (data) =>
  apiFetch('/api/v1/admin/programs', { method: 'POST', body: data })

// Users
export const listUsers = () => apiFetch('/api/v1/admin/users')
export const registerUser = (data) =>
  apiFetch('/api/v1/auth/register', { method: 'POST', body: data })
export const deactivateUser = (userId) =>
  apiFetch(`/api/v1/admin/users/${userId}`, { method: 'DELETE' })
