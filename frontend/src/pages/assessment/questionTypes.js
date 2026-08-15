// Metadata for the question types selectable via the generic "+ Add
// Question" type picker, used on normal (quiz/assignment/midterm/final)
// assessments. Must stay in sync with `QuestionType` in
// backend/app/models/question.py and the `type_data` shape convention
// documented in backend/app/schemas/question.py.
//
// Project and Lab are NOT here -- they're `Assessment.type` values now, each
// managed via its own dedicated panel (see LabProjectPanel.jsx) rather than
// this picker. Their `question_type` values still exist on `Question` rows
// under the hood, which is why QUESTION_TYPE_LABEL/emptyTypeData/typeSummary
// below still know about them.
export const QUESTION_TYPES = [
  { value: 'question', label: 'Question', mode: 'single' },
  { value: 'mcq', label: 'MCQ', mode: 'bulk' },
  { value: 'fill_blank', label: 'Fill in the Blanks', mode: 'bulk' },
  { value: 'true_false', label: 'True/False', mode: 'bulk' },
]

export const QUESTION_TYPE_LABEL = {
  question: 'Question',
  mcq: 'MCQ',
  fill_blank: 'Fill in the Blanks',
  true_false: 'True/False',
  project: 'Project',
  lab: 'Lab',
}

export const OPTION_LABELS = ['A', 'B', 'C', 'D']

// A fresh, empty `type_data` payload for a given type, so forms always
// start from a well-shaped object rather than undefined fields.
export function emptyTypeData(type) {
  switch (type) {
    case 'mcq':
      return {
        options: OPTION_LABELS.map((label) => ({ label, text: '' })),
        correct_option: 'A',
      }
    case 'fill_blank':
      return { answer: '' }
    case 'true_false':
      return { correct_answer: true }
    case 'project':
      return { description: '', deliverable: '' }
    case 'lab':
      return { description: '', tasks: '' }
    default:
      return null
  }
}

// A short one-line summary shown in the Questions table so faculty don't
// have to open a question to see what kind of item it is.
export function typeSummary(question) {
  const data = question.type_data
  switch (question.question_type) {
    case 'mcq': {
      const count = data?.options?.filter((o) => o.text)?.length ?? 0
      return `${count} option${count === 1 ? '' : 's'} · correct: ${data?.correct_option ?? '—'}`
    }
    case 'fill_blank':
      return data?.answer ? `Answer: ${data.answer}` : 'No answer set'
    case 'true_false':
      return `Answer: ${data?.correct_answer ? 'True' : 'False'}`
    case 'project':
    case 'lab':
      return data?.description ? truncate(data.description, 80) : '—'
    default:
      return ''
  }
}

function truncate(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}
