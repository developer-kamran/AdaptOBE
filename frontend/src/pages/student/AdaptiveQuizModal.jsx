import { useEffect, useState } from 'react'
import { getAdaptiveQuiz, submitAdaptiveQuiz } from '../../api/student'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Input from '../../components/ui/Input'
import Spinner from '../../components/ui/Spinner'
import EmptyState from '../../components/ui/EmptyState'

// A practice quiz drawn from the course question bank, weighted toward the
// student's weakest CLOs. Answers are graded client-visibly but never written
// to the official gradebook.
export default function AdaptiveQuizModal({ isOpen, onClose, course }) {
  const [quiz, setQuiz] = useState(null)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function loadQuiz() {
    setIsLoading(true)
    setResult(null)
    setAnswers({})
    try {
      setQuiz(await getAdaptiveQuiz(course.course_id))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) loadQuiz()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, course.course_id])

  function setAnswer(questionId, value) {
    setAnswers((current) => ({ ...current, [questionId]: value }))
  }

  async function handleSubmit() {
    setIsSubmitting(true)
    try {
      const payload = quiz.questions
        .filter((q) => answers[q.question_id] !== undefined)
        .map((q) => ({ question_id: q.question_id, answer: answers[q.question_id] }))
      setResult(await submitAdaptiveQuiz(course.course_id, payload))
    } finally {
      setIsSubmitting(false)
    }
  }

  const resultById = result
    ? Object.fromEntries(result.results.map((r) => [r.question_id, r]))
    : {}

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Practice Quiz — ${course.code}`}
      description="Focused on the CLOs you're weakest on. Practice only — not graded."
      width="max-w-2xl"
    >
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : !quiz || quiz.questions.length === 0 ? (
        <EmptyState
          title="No practice questions yet"
          description="This course has no auto-gradable (MCQ / True-False / Fill-in-the-blank) questions to practice with yet."
        />
      ) : (
        <div className="flex flex-col gap-5">
          {result && (
            <div className="rounded-lg bg-brand-50 border border-brand-200 px-4 py-3">
              <p className="text-sm font-semibold text-brand-800">
                You scored {result.correct} / {result.total} ({result.score_percentage.toFixed(0)}%)
              </p>
              {result.focus_clos.length > 0 && (
                <p className="text-xs text-brand-700 mt-1">
                  Keep practicing: {result.focus_clos.join(', ')}
                </p>
              )}
            </div>
          )}

          <ol className="flex flex-col gap-5 list-none">
            {quiz.questions.map((q, index) => {
              const graded = resultById[q.question_id]
              return (
                <li key={q.question_id} className="flex flex-col gap-2">
                  <div className="flex items-start gap-2">
                    <span className="text-sm font-medium text-ink-500 shrink-0">{index + 1}.</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-ink-900">{q.text}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge tone="neutral">{q.clo_code}</Badge>
                        {graded && (
                          <Badge tone={graded.correct ? 'success' : 'danger'}>
                            {graded.correct ? 'Correct' : 'Incorrect'}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="pl-6">
                    <QuestionInput
                      question={q}
                      value={answers[q.question_id]}
                      onChange={(v) => setAnswer(q.question_id, v)}
                      disabled={!!result}
                    />
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      )}

      {quiz && quiz.questions.length > 0 && (
        <ModalFooter>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          {result ? (
            <Button onClick={loadQuiz}>Try Another</Button>
          ) : (
            <Button onClick={handleSubmit} isLoading={isSubmitting}>
              Submit
            </Button>
          )}
        </ModalFooter>
      )}
    </Modal>
  )
}

function QuestionInput({ question, value, onChange, disabled }) {
  if (question.question_type === 'mcq') {
    return (
      <div className="flex flex-col gap-1.5">
        {(question.options ?? []).map((opt) => (
          <label key={opt.label} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name={`q-${question.question_id}`}
              checked={value === opt.label}
              onChange={() => onChange(opt.label)}
              disabled={disabled}
              className="h-4 w-4 text-brand-600 focus:ring-brand-500"
            />
            <span>
              <span className="font-medium">{opt.label}.</span> {opt.text}
            </span>
          </label>
        ))}
      </div>
    )
  }

  if (question.question_type === 'true_false') {
    return (
      <div className="flex items-center gap-4">
        {[
          { label: 'True', val: true },
          { label: 'False', val: false },
        ].map((opt) => (
          <label key={opt.label} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name={`q-${question.question_id}`}
              checked={value === opt.val}
              onChange={() => onChange(opt.val)}
              disabled={disabled}
              className="h-4 w-4 text-brand-600 focus:ring-brand-500"
            />
            {opt.label}
          </label>
        ))}
      </div>
    )
  }

  // fill_blank
  return (
    <Input
      placeholder="Your answer…"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="max-w-sm"
    />
  )
}
