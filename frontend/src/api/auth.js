import { apiFetch } from './client'

export function login(email, password) {
  return apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: { email, password },
    skipAuth: true,
  })
}
