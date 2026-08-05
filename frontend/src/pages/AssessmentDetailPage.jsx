import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  createQuestion,
  getAssessment,
  listQuestions,
  listScores,
  submitScores,
  suggestQuestionTag,
} from '../api/assessments'
import { listClos } from '../api/clos'
import { listEnrollments, listStudents } from '../api/enrollments'
import { ApiError } from '../api/client'
import Navbar from '../components/Navbar'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Textarea from '../components/ui/Textarea'
import Select from '../components/ui/Select'
import Modal, { ModalFooter } from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import Badge from '../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../components/ui/Table'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody, CardHeader } from '../components/ui/Card'

export default function AssessmentDetailPage() {
  const { courseId, assessmentId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [clos, setClos] = useState([])
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false)

  const loadQuestions = () => listQuestions(Number(assessmentId)).then(setQuestions)

  useEffect(() => {
    getAssessment(Number(assessmentId)).then(setAssessment)
    loadQuestions()
    listClos(Number(courseId)).then(setClos)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, courseId])

  const cloLookup = new Map(clos.map((c) => [c.id, c]))

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 flex flex-col gap-5">
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
              </p>
            </div>
          )}
        </div>

        <Card>
          <CardHeader
            title="Questions"
            description="Tag each question with the CLO it assesses."
            actions={
              <Button size="sm" onClick={() => setIsQuestionModalOpen(true)}>
                + Add Question
              </Button>
            }
          />
          <CardBody>
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
                    <TH>Marks</TH>
                    <TH>CLO Tag</TH>
                    <TH>Text</TH>
                  </TR>
                </THead>
                <TBody>
                  {questions.map((q) => (
                    <TR key={q.id}>
                      <TD className="font-medium">{q.question_number}</TD>
                      <TD>{q.marks}</TD>
                      <TD>
                        {q.clo_id ? (
                          <Badge tone="brand">{cloLookup.get(q.clo_id)?.code ?? `#${q.clo_id}`}</Badge>
                        ) : (
                          <span className="text-ink-400 text-xs">Untagged</span>
                        )}
                      </TD>
                      <TD className="text-ink-500 max-w-xs truncate">{q.text}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </CardBody>
        </Card>

        {questions && questions.length > 0 && (
          <ScoreEntryCard
            courseId={Number(courseId)}
            assessmentId={Number(assessmentId)}
            questions={questions}
          />
        )}
      </main>

      <AddQuestionModal
        isOpen={isQuestionModalOpen}
        onClose={() => setIsQuestionModalOpen(false)}
        onCreated={loadQuestions}
        assessmentId={Number(assessmentId)}
        clos={clos}
        nextNumber={(questions?.length ?? 0) + 1}
      />
    </div>
  )
}

function AddQuestionModal({ isOpen, onClose, onCreated, assessmentId, clos, nextNumber }) {
  const [questionNumber, setQuestionNumber] = useState(nextNumber)
  const [marks, setMarks] = useState('10')
  const [text, setText] = useState('')
  const [cloId, setCloId] = useState('')
  const [suggestions, setSuggestions] = useState(null)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setQuestionNumber(nextNumber)
      setMarks('10')
      setText('')
      setCloId('')
      setSuggestions(null)
      setError('')
    }
  }, [isOpen, nextNumber])

  async function handleSuggest() {
    if (!text.trim()) return
    setIsSuggesting(true)
    try {
      const result = await suggestQuestionTag(assessmentId, text)
      setSuggestions(result.suggestions)
    } catch {
      setSuggestions([])
    } finally {
      setIsSuggesting(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createQuestion(assessmentId, {
        question_number: Number(questionNumber),
        marks: Number(marks),
        clo_id: cloId ? Number(cloId) : undefined,
        text: text || undefined,
      })
      onClose()
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Question">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Question #"
            type="number"
            min="1"
            value={questionNumber}
            onChange={(e) => setQuestionNumber(e.target.value)}
            required
          />
          <Input
            label="Marks"
            type="number"
            min="0"
            value={marks}
            onChange={(e) => setMarks(e.target.value)}
            required
          />
        </div>
        <Textarea
          label="Question Text (optional)"
          placeholder="Design a normalised relational schema for..."
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm font-medium text-ink-700">CLO Tag</label>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleSuggest}
              isLoading={isSuggesting}
              disabled={!text.trim()}
            >
              Suggest with AI
            </Button>
          </div>
          <Select value={cloId} onChange={(e) => setCloId(e.target.value)}>
            <option value="">— Untagged —</option>
            {clos.map((clo) => (
              <option key={clo.id} value={clo.id}>
                {clo.code} — {clo.title}
              </option>
            ))}
          </Select>

          {suggestions && suggestions.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {suggestions.map((s) => (
                <button
                  key={s.clo_id}
                  type="button"
                  onClick={() => setCloId(String(s.clo_id))}
                  className={`text-xs rounded-full px-2.5 py-1 border transition-colors
                    ${
                      cloId === String(s.clo_id)
                        ? 'bg-brand-600 text-white border-brand-600'
                        : 'bg-white text-ink-700 border-border-strong hover:border-brand-400'
                    }`}
                >
                  {s.code} · {s.similarity_score.toFixed(2)}
                </button>
              ))}
            </div>
          )}
        </div>

        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create
          </Button>
        </ModalFooter>
      </form>
    </Modal>
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
