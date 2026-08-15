import { useState } from 'react'
import { deleteQuestion } from '../../api/assessments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import QuestionFormModal from './QuestionFormModal'
import { typeSummary } from './questionTypes'

const COPY = {
  lab: {
    title: 'Lab Components',
    description: 'Each component (e.g. performance, viva, report) is graded and tagged with the CLO it assesses.',
    empty: 'No lab components yet',
    addLabel: '+ Add Lab Component',
  },
  project: {
    title: 'Project Components',
    description: 'Each component (e.g. milestone, deliverable) is graded and tagged with the CLO it assesses.',
    empty: 'No project components yet',
    addLabel: '+ Add Project Component',
  },
}

// Management interface for Lab and Project assessments: a small set of
// graded components instead of the generic question-type picker used by
// quiz/assignment/midterm/final assessments (see AssessmentDetailPage.jsx
// and CHANGELOG.md). Each component is still a `Question` row under the
// hood (question_type 'lab'/'project'), so Score Entry keeps working
// unchanged -- only how these rows are created/managed differs.
export default function LabProjectPanel({
  assessmentType,
  assessmentId,
  questions,
  clos,
  cloLookup,
  nextNumber,
  remainingMarks,
  existingNumbers,
  onChanged,
}) {
  const [formModal, setFormModal] = useState(null) // { mode, question } | null
  const [error, setError] = useState('')
  const copy = COPY[assessmentType]

  async function handleDelete(question) {
    if (!window.confirm(`Delete "${question.text}"?`)) return
    setError('')
    try {
      await deleteQuestion(question.id)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <Card>
      <CardHeader
        title={copy.title}
        description={copy.description}
        actions={
          <Button size="sm" onClick={() => setFormModal({ mode: 'create', question: null })}>
            {copy.addLabel}
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
          <EmptyState title={copy.empty} />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>#</TH>
                <TH>Marks</TH>
                <TH>CLO Tag</TH>
                <TH>Title / Details</TH>
                <TH></TH>
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
                  <TD className="text-ink-500 max-w-xs">
                    <p className="truncate">{q.text}</p>
                    <p className="text-xs text-ink-400 mt-0.5 truncate">{typeSummary(q)}</p>
                  </TD>
                  <TD>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setFormModal({ mode: 'edit', question: q })}
                      >
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(q)}>
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

      {formModal && (
        <QuestionFormModal
          isOpen
          onClose={() => setFormModal(null)}
          onSaved={onChanged}
          assessmentId={assessmentId}
          clos={clos}
          nextNumber={nextNumber}
          mode={formModal.mode}
          type={assessmentType}
          question={formModal.question}
          remainingMarks={
            formModal.mode === 'edit' ? remainingMarks + (formModal.question?.marks ?? 0) : remainingMarks
          }
          existingNumbers={existingNumbers}
        />
      )}
    </Card>
  )
}
