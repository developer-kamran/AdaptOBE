import { apiFetch } from './client'

// Departments
export const listDepartments = () => apiFetch('/api/v1/admin/departments')
export const createDepartment = (data) =>
  apiFetch('/api/v1/admin/departments', { method: 'POST', body: data })
export const updateDepartment = (departmentId, data) =>
  apiFetch(`/api/v1/admin/departments/${departmentId}`, { method: 'PATCH', body: data })
export const deleteDepartment = (departmentId) =>
  apiFetch(`/api/v1/admin/departments/${departmentId}`, { method: 'DELETE' })

// Programs
export const listPrograms = () => apiFetch('/api/v1/admin/programs')
export const createProgram = (data) =>
  apiFetch('/api/v1/admin/programs', { method: 'POST', body: data })
export const updateProgram = (programId, data) =>
  apiFetch(`/api/v1/admin/programs/${programId}`, { method: 'PATCH', body: data })
export const deleteProgram = (programId) =>
  apiFetch(`/api/v1/admin/programs/${programId}`, { method: 'DELETE' })

// Users
export const listUsers = () => apiFetch('/api/v1/admin/users')
export const registerUser = (data) =>
  apiFetch('/api/v1/auth/register', { method: 'POST', body: data })
export const updateUser = (userId, data) =>
  apiFetch(`/api/v1/admin/users/${userId}`, { method: 'PATCH', body: data })
export const deactivateUser = (userId) =>
  apiFetch(`/api/v1/admin/users/${userId}`, { method: 'DELETE' })
export const getUserPassword = (userId) => apiFetch(`/api/v1/admin/users/${userId}/password`)

// Bulk student import (PDF/Excel). Preview parses and validates only —
// nothing is created until confirm.
export const previewStudentImport = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch('/api/v1/admin/students/import/preview', { method: 'POST', body: formData })
}
export const confirmStudentImport = (students) =>
  apiFetch('/api/v1/admin/students/import/confirm', { method: 'POST', body: { students } })
