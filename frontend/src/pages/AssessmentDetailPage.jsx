import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { deleteQuestion, getAssessment, listQuestions, listScores, submitScores } from '../api/assessments'
import { listClos } from '../api/clos'
import { listEnrollments, listStudents } from '../api/enrollments'
import { ApiError } from '../api/client'
import Navbar from '../components/Navbar'
import Button from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import Badge from '../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../components/ui/Table'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import QuestionTypeStep from './assessment/QuestionTypeStep'
import QuestionFormModal from './assessment/QuestionFormModal'
import BulkQuestionModal from './assessment/BulkQuestionModal'
import LabProjectPanel from './assessment/LabProjectPanel'
import { QUESTION_TYPE_LABEL, QUESTION_TYPES, typeSummary } from './assessment/questionTypes'

const LAB_PROJECT_TYPES = new Set(['lab', 'project'])

export default function AssessmentDetailPage() {
  const { courseId, assessmentId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [clos, setClos] = useState([])
  const [error, setError] = useState('')

  const [isTypeStepOpen, setIsTypeStepOpen] = useState(false)
  const [formModal, setFormModal] = useState(null) // { mode, type, question } | null
  const [bulkModal, setBulkModal] = useState(null) // { type, quantity } | null

  const loadQuestions = () => listQuestions(Number(assessmentId)).then(setQuestions)

  useEffect(() => {
    getAssessment(Number(assessmentId)).then(setAssessment)
    loadQuestions()
    listClos(Number(courseId)).then(setClos)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, courseId])

  const cloLookup = new Map(clos.map((c) => [c.id, c]))

  const existingNumbers = useMemo(
    () => new Set((questions ?? []).map((q) => q.question_number)),
    [questions],
  )
  const usedMarks = useMemo(() => (questions ?? []).reduce((sum, q) => sum + q.marks, 0), [questions])
  const remainingMarks = assessment ? assessment.total_marks - usedMarks : null
  const nextNumber = (questions?.length ?? 0) + 1

  function handleTypeContinue(type, quantity) {
    setIsTypeStepOpen(false)
    const meta = QUESTION_TYPES.find((t) => t.value === type)
    if (meta?.mode === 'bulk') {
      setBulkModal({ type, quantity })
    } else {
      setFormModal({ mode: 'create', type, question: null })
    }
  }

  async function handleDeleteQuestion(question) {
    if (!window.confirm(`Delete question #${question.question_number}?`)) return
    setError('')
    try {
      await deleteQuestion(question.id)
      loadQuestions()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-5">
        <div>
          <Link
            to={`/courses/${courseId}`}
            className="text-xs text-brand-600 hover:text-brand-700 font-medium"
          >
            ← Back to Course
          </Link>
          {assessment && (
            <div className="mt-1">
              <h1 className="text-xl font-semibold text-ink-900">{assessment.title}</h1>
              <p className="text-sm text-ink-500 mt-0.5">
                {assessment.total_marks} marks · {assessment.weightage_percent}% weightage
                {questions && (
                  <span className={remainingMarks < 0 ? 'text-danger-600' : ''}>
                    {' '}
                    · {usedMarks}/{assessment.total_marks} marks used
                  </span>
                )}
              </p>
            </div>
          )}
        </div>

        {assessment && LAB_PROJECT_TYPES.has(assessment.type) ? (
          <LabProjectPanel
            assessmentType={assessment.type}
            assessmentId={Number(assessmentId)}
            questions={questions}
            clos={clos}
            cloLookup={cloLookup}
            nextNumber={nextNumber}
            remainingMarks={remainingMarks}
            existingNumbers={existingNumbers}
            onChanged={loadQuestions}
          />
        ) : (
          <Card>
            <CardHeader
              title="Questions"
              description="Tag each question with the CLO it assesses."
              actions={
                <Button size="sm" onClick={() => setIsTypeStepOpen(true)}>
                  + Add Question
                </Button>
              }
            />
            <CardBody>
              {error && (
                <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
              )}
              {questions === null ? (
                <div className="flex justify-center py-8">
                  <Spinner />
                </div>
              ) : questions.length === 0 ? (
                <EmptyState title="No questions yet" />
              ) : (
                <Table>
                  <THead>
                    <TR>
                      <TH>#</TH>
                      <TH>Type</TH>
                      <TH>Marks</TH>
                      <TH>CLO Tag</TH>
                      <TH>Text / Details</TH>
                      <TH></TH>
                    </TR>
                  </THead>
                  <TBody>
                    {questions.map((q) => (
                      <TR key={q.id}>
                        <TD className="font-medium">{q.question_number}</TD>
                        <TD>
                          <Badge tone="neutral">{QUESTION_TYPE_LABEL[q.question_type] ?? q.question_type}</Badge>
                        </TD>
                        <TD>{q.marks}</TD>
                        <TD>
                          {q.clo_id ? (
                            <Badge tone="brand">{cloLookup.get(q.clo_id)?.code ?? `#${q.clo_id}`}</Badge>
                          ) : (
                            <span className="text-ink-400 text-xs">Untagged</span>
                          )}
                        </TD>
                        <TD className="text-ink-500 max-w-xs">
                          <p className="truncate">{q.text}</p>
                          {q.question_type !== 'question' && (
                            <p className="text-xs text-ink-400 mt-0.5 truncate">{typeSummary(q)}</p>
                          )}
                        </TD>
                        <TD>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                setFormModal({ mode: 'edit', type: q.question_type, question: q })
                              }
                            >
                              Edit
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteQuestion(q)}>
                              Delete
                            </Button>
                          </div>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </CardBody>
          </Card>
        )}

        {questions && questions.length > 0 && (
          <ScoreEntryCard
            courseId={Number(courseId)}
            assessmentId={Number(assessmentId)}
            questions={questions}
          />
        )}
      </main>

      <QuestionTypeStep
        isOpen={isTypeStepOpen}
        onClose={() => setIsTypeStepOpen(false)}
        onContinue={handleTypeContinue}
      />

      {formModal && (
        <QuestionFormModal
          isOpen
          onClose={() => setFormModal(null)}
          onSaved={loadQuestions}
          assessmentId={Number(assessmentId)}
          clos={clos}
          nextNumber={nextNumber}
          mode={formModal.mode}
          type={formModal.type}
          question={formModal.question}
          remainingMarks={
            formModal.mode === 'edit'
              ? remainingMarks + (formModal.question?.marks ?? 0)
              : remainingMarks
          }
          existingNumbers={existingNumbers}
        />
      )}

      {bulkModal && (
        <BulkQuestionModal
          isOpen
          onClose={() => setBulkModal(null)}
          onSaved={loadQuestions}
          assessmentId={Number(assessmentId)}
          clos={clos}
          nextNumber={nextNumber}
          type={bulkModal.type}
          quantity={bulkModal.quantity}
          remainingMarks={remainingMarks}
          existingNumbers={existingNumbers}
        />
      )}
    </div>
  )
}

function ScoreEntryCard({ courseId, assessmentId, questions }) {
  const [students, setStudents] = useState(null)
  const [grid, setGrid] = useState({}) // `${studentId}:${questionId}` -> string
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      const [enrollments, allStudents, existingScores] = await Promise.all([
        listEnrollments(courseId),
        listStudents(),
        listScores(assessmentId),
      ])
      const lookup = new Map(allStudents.map((s) => [s.id, s]))
      const roster = enrollments
        .map((e) => lookup.get(e.student_id))
        .filter(Boolean)
        .sort((a, b) => a.full_name.localeCompare(b.full_name))
      setStudents(roster)

      const initialGrid = {}
      for (const score of existingScores) {
        initialGrid[`${score.student_id}:${score.question_id}`] = String(score.marks_obtained)
      }
      setGrid(initialGrid)
    })()
  }, [courseId, assessmentId])

  function setCell(studentId, questionId, value) {
    setGrid((current) => ({ ...current, [`${studentId}:${questionId}`]: value }))
  }

  async function handleSave() {
    setError('')
    setMessage('')
    setIsSaving(true)
    try {
      const scores = []
      for (const student of students) {
        for (const question of questions) {
          const raw = grid[`${student.id}:${question.id}`]
          if (raw === undefined || raw === '') continue
          scores.push({
            question_id: question.id,
            student_id: student.id,
            marks_obtained: Number(raw),
          })
        }
      }
      const result = await submitScores(assessmentId, scores)
      setMessage(`Saved ${result.saved} score(s) · attainment recalculated for ${result.recalculated_students} student(s).`)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader
        title="Score Entry"
        description="Enter marks per question. Blank cells are left unsaved."
        actions={
          <Button size="sm" onClick={handleSave} isLoading={isSaving}>
            Save Scores
          </Button>
        }
      />
      <CardBody>
        {students === null ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : students.length === 0 ? (
          <EmptyState title="No students enrolled" description="Enroll students in the Enrollments tab first." />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Student</TH>
                {questions.map((q) => (
                  <TH key={q.id} className="text-center">
                    Q{q.question_number} <span className="text-ink-400">/{q.marks}</span>
                  </TH>
                ))}
              </TR>
            </THead>
            <TBody>
              {students.map((student) => (
                <TR key={student.id}>
                  <TD className="font-medium whitespace-nowrap">{student.full_name}</TD>
                  {questions.map((q) => (
                    <TD key={q.id} className="text-center">
                      <input
                        type="number"
                        min="0"
                        max={q.marks}
                        step="0.5"
                        value={grid[`${student.id}:${q.id}`] ?? ''}
                        onChange={(e) => setCell(student.id, q.id, e.target.value)}
                        className="w-16 h-8 rounded-md border border-border-strong text-center text-sm
                          focus:border-brand-500"
                      />
                    </TD>
                  ))}
                </TR>
              ))}
            </TBody>
          </Table>
        )}

        {message && (
          <p className="text-sm text-success-700 bg-success-50 rounded-lg px-3 py-2 mt-4">{message}</p>
        )}
        {error && (
          <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mt-4">{error}</p>
        )}
      </CardBody>
    </Card>
  )
}
