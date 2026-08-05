import { apiFetch } from './client'

export function listMyCourses() {
  return apiFetch('/api/v1/courses?mine=true')
}
