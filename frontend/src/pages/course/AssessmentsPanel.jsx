import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createAssessment,
  deleteAssessment,
  listAssessments,
  updateAssessment,
} from '../../api/assessments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

const TYPE_LABEL = {
  quiz: 'Quiz',
  assignment: 'Assignment',
  lab: 'Lab',
  project: 'Project',
  midterm: 'Midterm',
  final: 'Final',
}

export default function AssessmentsPanel({ course }) {
  const [assessments, setAssessments] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = () => listAssessments(course.id).then(setAssessments)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course.id])

  async function handleDelete(e, assessment) {
    e.stopPropagation()
    if (!window.confirm(`Delete assessment "${assessment.title}"? This also removes its questions and scores.`))
      return
    setError('')
    try {
      await deleteAssessment(assessment.id)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  const totalWeightage = (assessments ?? []).reduce((sum, a) => sum + a.weightage_percent, 0)

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">
          Assessments for {course.code}
          {assessments && (
            <span className={totalWeightage > 100 ? 'text-danger-600' : ''}>
              {' '}
              · {totalWeightage}% of 100% weightage used
            </span>
          )}
        </p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
          + Add Assessment
        </Button>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {assessments === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : assessments.length === 0 ? (
        <EmptyState title="No assessments yet" description="Add a quiz, assignment or exam to start scoring students." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Title</TH>
              <TH>Type</TH>
              <TH>Total Marks</TH>
              <TH>Weightage</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {assessments.map((assessment) => (
              <TR
                key={assessment.id}
                className="cursor-pointer"
                onClick={() => navigate(`/courses/${course.id}/assessments/${assessment.id}`)}
              >
                <TD className="font-medium">{assessment.title}</TD>
                <TD>
                  <Badge tone="neutral">{TYPE_LABEL[assessment.type]}</Badge>
                </TD>
                <TD>{assessment.total_marks}</TD>
                <TD>{assessment.weightage_percent}%</TD>
                <TD>
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditing(assessment)
                      }}
                    >
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={(e) => handleDelete(e, assessment)}>
                      Delete
                    </Button>
                    <span className="text-brand-600 text-xs font-medium">Manage →</span>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <AssessmentFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaved={load}
        courseId={course.id}
        mode="create"
      />
      <AssessmentFormModal
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={load}
        courseId={course.id}
        mode="edit"
        assessment={editing}
      />
    </div>
  )
}

function AssessmentFormModal({ isOpen, onClose, onSaved, courseId, mode, assessment }) {
  const [title, setTitle] = useState('')
  const [type, setType] = useState('quiz')
  const [totalMarks, setTotalMarks] = useState('10')
  const [weightagePercent, setWeightagePercent] = useState('10')
  const [date, setDate] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setTitle(assessment?.title ?? '')
      setType(assessment?.type ?? 'quiz')
      setTotalMarks(assessment ? String(assessment.total_marks) : '10')
      setWeightagePercent(assessment ? String(assessment.weightage_percent) : '10')
      setDate(assessment?.date ?? '')
      setError('')
    }
  }, [isOpen, assessment])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const data = {
        title,
        type,
        total_marks: Number(totalMarks),
        weightage_percent: Number(weightagePercent),
        date: date || undefined,
      }
      if (mode === 'edit') {
        await updateAssessment(assessment.id, data)
      } else {
        await createAssessment({ course_id: courseId, ...data })
      }
      onClose()
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={mode === 'edit' ? 'Edit Assessment' : 'Add Assessment'}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Title"
          placeholder="Midterm Exam"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Select label="Type" value={type} onChange={(e) => setType(e.target.value)}>
          {Object.entries(TYPE_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Total Marks"
            type="number"
            min="0"
            value={totalMarks}
            onChange={(e) => setTotalMarks(e.target.value)}
            required
          />
          <Input
            label="Weightage %"
            type="number"
            min="0"
            max="100"
            value={weightagePercent}
            onChange={(e) => setWeightagePercent(e.target.value)}
            required
          />
        </div>
        <Input label="Date (optional)" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {mode === 'edit' ? 'Save' : 'Create'}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
