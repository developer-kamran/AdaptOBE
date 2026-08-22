import { apiFetch, downloadExport, fetchExportBlob } from './client'

export const listAssessments = (courseId) =>
  apiFetch(`/api/v1/assessments?course_id=${courseId}`)

export const getAssessment = (assessmentId) => apiFetch(`/api/v1/assessments/${assessmentId}`)

export const createAssessment = (data) =>
  apiFetch('/api/v1/assessments', { method: 'POST', body: data })

export const updateAssessment = (assessmentId, data) =>
  apiFetch(`/api/v1/assessments/${assessmentId}`, { method: 'PATCH', body: data })

export const deleteAssessment = (assessmentId) =>
  apiFetch(`/api/v1/assessments/${assessmentId}`, { method: 'DELETE' })

// Questions
export const listQuestions = (assessmentId) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/questions`)

export const createQuestion = (assessmentId, data) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/questions`, { method: 'POST', body: data })

export const createQuestionsBulk = (assessmentId, items) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/questions/bulk`, {
    method: 'POST',
    body: { items },
  })

export const updateQuestion = (questionId, data) =>
  apiFetch(`/api/v1/assessments/questions/${questionId}`, { method: 'PATCH', body: data })

export const deleteQuestion = (questionId) =>
  apiFetch(`/api/v1/assessments/questions/${questionId}`, { method: 'DELETE' })

export const suggestQuestionTag = (assessmentId, text, limit = 3) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/questions/suggest-tag`, {
    method: 'POST',
    body: { text, limit },
  })

// Scores
export const listScores = (assessmentId) => apiFetch(`/api/v1/assessments/${assessmentId}/scores`)

export const submitScores = (assessmentId, scores) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/scores`, {
    method: 'POST',
    body: { scores },
  })

// Export
export const previewAssessmentExportPdf = (assessmentId) =>
  fetchExportBlob(`/api/v1/assessments/${assessmentId}/export/pdf`, 'assessment.pdf')

export const downloadAssessmentExportDocx = (assessmentId) =>
  downloadExport(`/api/v1/assessments/${assessmentId}/export/docx`, 'assessment.docx')

// Score upload
export const previewScoreImport = (assessmentId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch(`/api/v1/assessments/${assessmentId}/scores/import/preview`, {
    method: 'POST',
    body: formData,
  })
}

export const confirmScoreImport = (assessmentId, scores) =>
  apiFetch(`/api/v1/assessments/${assessmentId}/scores/import/confirm`, {
    method: 'POST',
    body: { scores },
  })

// Assessment paper upload -> extracted questions
export const previewPaperImport = (assessmentId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch(`/api/v1/assessments/${assessmentId}/paper-import/preview`, {
    method: 'POST',
    body: formData,
  })
}
