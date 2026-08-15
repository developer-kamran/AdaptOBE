import { useState } from 'react'
import { confirmEnrollmentImport, previewEnrollmentImport } from '../../api/enrollments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'

const FIELD_LABELS = {
  full_name: 'Full Name',
  father_name: "Father's Name",
  enrollment_no: 'Enrollment No',
  seat_no: 'Seat No',
  eligible: 'Eligible',
}

const STATUS_BADGE = {
  ready: { tone: 'success', label: 'Ready' },
  ineligible: { tone: 'warning', label: 'Ineligible' },
  not_found: { tone: 'danger', label: 'Not found' },
  wrong_programme: { tone: 'danger', label: 'Wrong programme' },
  already_enrolled: { tone: 'neutral', label: 'Already enrolled' },
  duplicate_in_file: { tone: 'danger', label: 'Duplicate in file' },
}

export default function EnrollImportModal({ isOpen, onClose, onEnrolled, course }) {
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
    if (result?.enrolledCount) onEnrolled()
    reset()
    onClose()
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError('')
    setIsBusy(true)
    try {
      const data = await previewEnrollmentImport(course.id, file)
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
      const ready = preview.records.filter((r) => r.status === 'ready')
      const enrolled = await confirmEnrollmentImport(
        course.id,
        ready.map((r) => r.matched_student_id),
      )
      setResult({ enrolledCount: enrolled.length, ready })
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
      title="Add Students via File"
      description={
        step === 'upload'
          ? 'Upload an Excel or PDF roster. Rows are matched to existing student accounts — nothing is enrolled until you review and confirm.'
          : step === 'preview'
            ? 'Review the matched records before enrolling them.'
            : 'Enrollment complete.'
      }
    >
      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {step === 'upload' && (
        <UploadStep
          file={file}
          setFile={setFile}
          isBusy={isBusy}
          onSubmit={handleUpload}
          onCancel={handleClose}
        />
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
        <label htmlFor="enroll-roster-file" className="text-sm font-medium text-ink-700">
          Roster file
        </label>
        <input
          id="enroll-roster-file"
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
        <p className="text-xs font-medium text-ink-700 mb-1">The file should contain a column for each of:</p>
        <p className="text-xs text-ink-500">{Object.values(FIELD_LABELS).join(' · ')}</p>
        <p className="text-xs text-ink-500 mt-1.5">
          Column headings don't have to match exactly — they're matched by meaning. Each row
          must match an <strong>existing</strong> student account by Enrollment No or Seat No;
          this does not create new accounts. Rows marked "Eligible" = No are not enrolled.
        </p>
      </div>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isBusy} disabled={!file}>
          Extract Students
        </Button>
      </ModalFooter>
    </form>
  )
}

function PreviewStep({ preview, isBusy, onConfirm, onBack }) {
  const {
    total_detected,
    ready_count,
    ineligible_count,
    not_found_count,
    wrong_programme_count,
    already_enrolled_count,
    duplicate_count,
    records,
    detected_columns,
    warnings,
  } = preview

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <SummaryTile label="Detected" value={total_detected} tone="neutral" />
        <SummaryTile label="Ready to enroll" value={ready_count} tone="success" />
        <SummaryTile label="Ineligible" value={ineligible_count} tone="warning" />
        <SummaryTile label="Not found" value={not_found_count} tone="danger" />
        <SummaryTile label="Wrong programme" value={wrong_programme_count} tone="danger" />
        <SummaryTile label="Already enrolled" value={already_enrolled_count} tone="neutral" />
      </div>
      {duplicate_count > 0 && (
        <SummaryTile label="Duplicate rows in file" value={duplicate_count} tone="danger" />
      )}

      {warnings.map((warning) => (
        <p key={warning} className="text-sm text-warning-700 bg-warning-50 rounded-lg px-3 py-2">
          {warning}
        </p>
      ))}

      <div>
        <p className="text-xs font-medium text-ink-700 mb-1.5">Columns detected in your file</p>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(FIELD_LABELS).map(([field, label]) => (
            <Badge key={field} tone={detected_columns[field] ? 'brand' : 'danger'}>
              {label}
              {detected_columns[field] ? ` → "${detected_columns[field]}"` : ' → not found'}
            </Badge>
          ))}
        </div>
      </div>

      {records.length === 0 ? (
        <p className="text-sm text-ink-500 py-6 text-center">
          No student rows could be read from this file.
        </p>
      ) : (
        <div className="max-h-80 overflow-y-auto border border-border rounded-lg">
          <Table>
            <THead>
              <TR>
                <TH>Row</TH>
                <TH>Full Name</TH>
                <TH>Enrollment No</TH>
                <TH>Seat No</TH>
                <TH>Eligible</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {records.map((record) => {
                const badge = STATUS_BADGE[record.status]
                return (
                  <TR key={record.row_number} className={record.status === 'ready' ? '' : 'bg-slate-50/60'}>
                    <TD className="text-ink-500">{record.row_number}</TD>
                    <TD>{record.full_name ?? <Missing />}</TD>
                    <TD>{record.enrollment_no ?? <Missing />}</TD>
                    <TD>{record.seat_no ?? <Missing />}</TD>
                    <TD>{record.eligible === null ? '—' : record.eligible ? 'Yes' : 'No'}</TD>
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
        Only rows marked "Ready" will be enrolled. Everything else is listed for your review and
        will not be added.
      </p>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="button" onClick={onConfirm} isLoading={isBusy} disabled={ready_count === 0}>
          Enroll {ready_count} Student{ready_count === 1 ? '' : 's'}
        </Button>
      </ModalFooter>
    </div>
  )
}

function ResultStep({ result, onClose }) {
  return (
    <div className="flex flex-col gap-4">
      <SummaryTile label="Students enrolled" value={result.enrolledCount} tone="success" />
      <div className="max-h-64 overflow-y-auto border border-border rounded-lg">
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Enrollment No</TH>
            </TR>
          </THead>
          <TBody>
            {result.ready.map((row) => (
              <TR key={row.row_number}>
                <TD className="font-medium">{row.full_name}</TD>
                <TD className="text-ink-500">{row.enrollment_no}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </div>
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
