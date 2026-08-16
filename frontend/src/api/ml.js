import { apiFetch } from './client'

// Runs the XGBoost model and persists fresh predictions.
export function predictRisk(courseId) {
  return apiFetch(`/api/v1/ml/predict-risk/${courseId}`, { method: 'POST' })
}

// Returns the last persisted predictions without re-running the model.
export function getStoredRisk(courseId) {
  return apiFetch(`/api/v1/ml/predict-risk/${courseId}`)
}
