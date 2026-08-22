import { useEffect, useState } from 'react'
import { getStoredRisk, predictRisk } from '../api/ml'
import { listStudents } from '../api/enrollments'
import { Card, CardBody, CardHeader } from './ui/Card'
import { Table, THead, TH, TBody, TR, TD } from './ui/Table'
import Button from './ui/Button'
import Badge from './ui/Badge'
import Spinner from './ui/Spinner'
import EmptyState from './ui/EmptyState'
import InfoTooltip from './ui/InfoTooltip'

const RISK_TONE = { high: 'danger', medium: 'warning', low: 'success' }

function prettyFeature(name) {
  return name.replace(/_/g, ' ').replace(/percentage|score/gi, '').trim()
}

// SHAP contributions rendered as a plain-language popover -- the qualitative
// "why", with the raw shap values kept secondary, mirroring how the CLO<->PLO
// matching UI surfaces its similarity score behind an InfoTooltip.
function ShapExplanation({ shap }) {
  const top = [...shap.feature_contributions]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .slice(0, 3)
  return (
    <InfoTooltip>
      <p className="font-medium mb-1">Why this prediction</p>
      <ul className="space-y-1">
        {top.map((c) => (
          <li key={c.feature} className="flex items-center justify-between gap-2">
            <span className="capitalize">
              {prettyFeature(c.feature)} ({c.value.toFixed(0)})
            </span>
            <span className={c.impact === 'increased_risk' ? 'text-red-300' : 'text-green-300'}>
              {c.impact === 'increased_risk' ? '↑ risk' : '↓ risk'}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5 text-ink-300 text-[11px]">
        XGBoost · SHAP feature attribution
      </p>
    </InfoTooltip>
  )
}

export default function RiskPanel({ courseId }) {
  const [students, setStudents] = useState(new Map())
  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState('')
  // GET (stored) never carries `skipped` -- only a fresh POST run tells us who
  // was excluded and why, so the "why nothing predicted" message is only
  // accurate once this is true.
  const [hasRunOnce, setHasRunOnce] = useState(false)

  useEffect(() => {
    if (!courseId) return
    setError('')
    setIsLoading(true)
    ;(async () => {
      try {
        const [stored, allStudents] = await Promise.all([
          getStoredRisk(courseId),
          listStudents(),
        ])
        setStudents(new Map(allStudents.map((s) => [s.id, s])))
        setReport({ ...stored, skipped: stored.skipped ?? [] })
      } finally {
        setIsLoading(false)
      }
    })()
  }, [courseId])

  async function handleRun() {
    setError('')
    setIsRunning(true)
    try {
      const fresh = await predictRisk(courseId)
      setReport({ ...fresh, skipped: fresh.skipped ?? [] })
      setHasRunOnce(true)
    } catch (err) {
      setError(err?.detail || 'Prediction failed.')
    } finally {
      setIsRunning(false)
    }
  }

  const predictions = report?.predictions ?? []
  const skipped = report?.skipped ?? []
  const gaps = report?.learning_gaps ?? []

  const skippedNote = skipped.length > 0 && (
    <p className="text-xs text-ink-500">
      {skipped.length} student{skipped.length > 1 ? 's' : ''} skipped (fewer than 5 scored
      assessments).
    </p>
  )

  const gapsSection = gaps.length > 0 && (
    <div>
      <h4 className="text-sm font-semibold text-ink-900 mb-2">
        Learning gaps — CLOs below threshold
      </h4>
      <div className="flex flex-wrap gap-2">
        {gaps.map((gap) => (
          <Badge key={gap.clo_id} tone="warning">
            {gap.code}: {gap.class_average.toFixed(0)}% &lt; {gap.threshold.toFixed(0)}%
          </Badge>
        ))}
      </div>
    </div>
  )

  return (
    <Card>
      <CardHeader
        title="Student Risk Prediction"
        description="XGBoost risk level per student, with SHAP explanations and weak-CLO gaps"
        actions={
          <Button size="sm" onClick={handleRun} isLoading={isRunning}>
            Run Prediction
          </Button>
        }
      />
      <CardBody>
        {error && (
          <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : predictions.length === 0 ? (
          <div className="flex flex-col gap-4">
            <EmptyState
              title={hasRunOnce ? "No students could be scored" : "No predictions yet"}
              description={
                hasRunOnce && skipped.length > 0
                  ? `${skipped.length} enrolled student${skipped.length > 1 ? 's have' : ' has'} fewer than 5 scored assessments, so risk can't be predicted yet. Enter more scores (and attendance) on the course page, then run the prediction again.`
                  : hasRunOnce
                    ? "No enrolled students have any scored assessments yet. Enter scores on the course page, then run the prediction again."
                    : "Run a prediction to classify each student's risk. Students need at least 5 scored assessments; enter attendance on the course page first for the best signal."
              }
            />
            {skippedNote}
            {gapsSection}
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <Table>
              <THead>
                <TR>
                  <TH>Student</TH>
                  <TH>Seat No.</TH>
                  <TH>Risk</TH>
                  <TH>Confidence</TH>
                  <TH>Predicted Score</TH>
                  <TH>Why</TH>
                </TR>
              </THead>
              <TBody>
                {predictions.map((p) => {
                  const student = students.get(p.student_id)
                  return (
                    <TR key={p.student_id}>
                      <TD className="font-medium">
                        {p.full_name || student?.full_name || `#${p.student_id}`}
                      </TD>
                      <TD className="text-ink-500">{p.seat_no || student?.seat_no || '—'}</TD>
                      <TD>
                        <Badge tone={RISK_TONE[p.risk_level] ?? 'neutral'}>
                          {p.risk_level}
                        </Badge>
                      </TD>
                      <TD className="text-ink-500">{(p.confidence_score * 100).toFixed(0)}%</TD>
                      <TD className="text-ink-500">{p.predicted_score.toFixed(0)}%</TD>
                      <TD>
                        <ShapExplanation shap={p.shap_explanation} />
                      </TD>
                    </TR>
                  )
                })}
              </TBody>
            </Table>

            {skippedNote}
            {gapsSection}
          </div>
        )}
      </CardBody>
    </Card>
  )
}
