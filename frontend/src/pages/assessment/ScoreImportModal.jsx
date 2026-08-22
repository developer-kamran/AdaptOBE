import { useState } from 'react'
import { confirmScoreImport, previewScoreImport } from '../../api/assessments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'

const STATUS_BADGE = {
  ready: { tone: 'success', label: 'Ready' },
  student_not_found: { tone: 'danger', label: 'Not found' },
  duplicate_in_file: { tone: 'danger', label: 'Duplicate in file' },
  no_marks: { tone: 'warning', label: 'No valid marks' },
}

export default function ScoreImportModal({ isOpen, onClose, onImported, assessmentId }) {
  const [step, setStep] = useState('upload') // upload | preview | result
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isBusy, setIsBusy] = useState(false)

  function reset() {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setResult(null)
    setError('')
    setIsBusy(false)
  }

  function handleClose() {
    if (result?.saved) onImported()
    reset()
    onClose()
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError('')
    setIsBusy(true)
    try {
      const data = await previewScoreImport(assessmentId, file)
      setPreview(data)
      setStep('preview')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not read that file.')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleConfirm() {
    setError('')
    setIsBusy(true)
    try {
      const scores = []
      for (const record of preview.records) {
        if (record.status !== 'ready') continue
        for (const [questionId, marks] of Object.entries(record.marks)) {
          scores.push({
            question_id: Number(questionId),
            student_id: record.matched_student_id,
            marks_obtained: marks,
          })
        }
      }
      const response = await confirmScoreImport(assessmentId, scores)
      setResult(response)
      setStep('result')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      width="max-w-5xl"
      title="Upload Scores"
      description={
        step === 'upload'
          ? 'Upload an Excel or PDF sheet with one column per question and one row per student.'
          : step === 'preview'
            ? 'Review the matched records before saving.'
            : 'Scores saved.'
      }
    >
      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {step === 'upload' && (
        <UploadStep file={file} setFile={setFile} isBusy={isBusy} onSubmit={handleUpload} onCancel={handleClose} />
      )}

      {step === 'preview' && preview && (
        <PreviewStep
          preview={preview}
          isBusy={isBusy}
          onConfirm={handleConfirm}
          onBack={() => {
            setPreview(null)
            setError('')
            setStep('upload')
          }}
        />
      )}

      {step === 'result' && result && <ResultStep result={result} onClose={handleClose} />}
    </Modal>
  )
}

function UploadStep({ file, setFile, isBusy, onSubmit, onCancel }) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="score-sheet-file" className="text-sm font-medium text-ink-700">
          Score sheet
        </label>
        <input
          id="score-sheet-file"
          type="file"
          accept=".xlsx,.xls,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-ink-700 file:mr-3 file:rounded-lg file:border-0
            file:bg-brand-600 file:px-3 file:py-2 file:text-sm file:font-medium
            file:text-white hover:file:bg-brand-700"
          required
        />
      </div>

      <div className="rounded-lg bg-slate-50 border border-border px-3 py-2.5">
        <p className="text-xs font-medium text-ink-700 mb-1">
          One column per question (e.g. "Q1", "Q2"...), one row per student, plus a Name or Seat No.
          column to identify them.
        </p>
        <p className="text-xs text-ink-500">
          Column headings don't have to match exactly — they're matched by meaning or position.
          Only students already enrolled in this course will be matched. This does not affect the
          manual Score Entry grid below.
        </p>
      </div>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isBusy} disabled={!file}>
          Extract Scores
        </Button>
      </ModalFooter>
    </form>
  )
}

function PreviewStep({ preview, isBusy, onConfirm, onBack }) {
  const {
    total_detected,
    ready_count,
    student_not_found_count,
    duplicate_count,
    no_marks_count,
    records,
    detected_columns,
    detected_question_columns,
    warnings,
  } = preview

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryTile label="Detected" value={total_detected} tone="neutral" />
        <SummaryTile label="Ready to save" value={ready_count} tone="success" />
        <SummaryTile label="Not found" value={student_not_found_count} tone="danger" />
        <SummaryTile label="Duplicate / no marks" value={duplicate_count + no_marks_count} tone="warning" />
      </div>

      {warnings.map((warning) => (
        <p key={warning} className="text-sm text-warning-700 bg-warning-50 rounded-lg px-3 py-2">
          {warning}
        </p>
      ))}

      <div>
        <p className="text-xs font-medium text-ink-700 mb-1.5">Columns detected</p>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={detected_columns.full_name ? 'brand' : 'neutral'}>
            Full Name{detected_columns.full_name ? ` → "${detected_columns.full_name}"` : ' → not found'}
          </Badge>
          <Badge tone={detected_columns.seat_no ? 'brand' : 'neutral'}>
            Seat No.{detected_columns.seat_no ? ` → "${detected_columns.seat_no}"` : ' → not found'}
          </Badge>
          {detected_question_columns.map((c) => (
            <Badge key={c.question_id} tone={c.header ? 'brand' : 'danger'}>
              Q{c.question_number}
              {c.header ? ` → "${c.header}"${c.matched_by === 'position' ? ' (by position)' : ''}` : ' → not found'}
            </Badge>
          ))}
        </div>
      </div>

      {records.length === 0 ? (
        <p className="text-sm text-ink-500 py-6 text-center">No student rows could be read from this file.</p>
      ) : (
        <div className="max-h-80 overflow-y-auto border border-border rounded-lg">
          <Table>
            <THead>
              <TR>
                <TH>Row</TH>
                <TH>Name / Seat No.</TH>
                <TH>Marks</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {records.map((record) => {
                const badge = STATUS_BADGE[record.status]
                const rejectedCount = Object.keys(record.rejected_marks ?? {}).length
                return (
                  <TR key={record.row_number} className={record.status === 'ready' ? '' : 'bg-slate-50/60'}>
                    <TD className="text-ink-500">{record.row_number}</TD>
                    <TD>{record.full_name ?? record.seat_no ?? <Missing />}</TD>
                    <TD className="text-ink-500">
                      {Object.keys(record.marks ?? {}).length} matched
                      {rejectedCount > 0 && `, ${rejectedCount} rejected`}
                    </TD>
                    <TD>
                      <span className="flex flex-col gap-1 items-start">
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                        {record.status !== 'ready' && (
                          <span className="text-xs text-ink-500">{record.detail}</span>
                        )}
                      </span>
                    </TD>
                  </TR>
                )
              })}
            </TBody>
          </Table>
        </div>
      )}

      <p className="text-xs text-ink-500">
        Only rows marked "Ready" will be saved. Everything else is listed for your review and will
        not be added.
      </p>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="button" onClick={onConfirm} isLoading={isBusy} disabled={ready_count === 0}>
          Save Scores for {ready_count} Student{ready_count === 1 ? '' : 's'}
        </Button>
      </ModalFooter>
    </div>
  )
}

function ResultStep({ result, onClose }) {
  return (
    <div className="flex flex-col gap-4">
      <SummaryTile label="Scores saved" value={result.saved} tone="success" />
      <p className="text-sm text-ink-500">
        Attainment recalculated for {result.recalculated_students} student(s).
      </p>
      <ModalFooter>
        <Button type="button" onClick={onClose}>
          Done
        </Button>
      </ModalFooter>
    </div>
  )
}

function SummaryTile({ label, value, tone }) {
  const TONES = {
    neutral: 'bg-slate-50 text-ink-900 border-border',
    success: 'bg-success-50 text-success-700 border-green-200',
    warning: 'bg-warning-50 text-warning-700 border-amber-200',
    danger: 'bg-danger-50 text-danger-700 border-red-200',
  }
  return (
    <div className={`rounded-lg border px-3 py-2.5 ${TONES[tone]}`}>
      <p className="text-xl font-semibold leading-tight">{value}</p>
      <p className="text-xs mt-0.5 opacity-80">{label}</p>
    </div>
  )
}

function Missing() {
  return <span className="text-danger-600 text-xs">—</span>
}
