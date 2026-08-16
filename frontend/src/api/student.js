import { apiFetch } from './client'

export function getProgress() {
  return apiFetch('/api/v1/student/progress')
}

export function getCourseScores(courseId) {
  return apiFetch(`/api/v1/student/courses/${courseId}/scores`)
}

export function getAdaptiveQuiz(courseId) {
  return apiFetch(`/api/v1/student/courses/${courseId}/adaptive-quiz`)
}

export function submitAdaptiveQuiz(courseId, answers) {
  return apiFetch(`/api/v1/student/courses/${courseId}/adaptive-quiz/submit`, {
    method: 'POST',
    body: { answers },
  })
}
