import { useState } from 'react'
import { confirmStudentImport, previewStudentImport } from '../../api/admin'
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
  email: 'Email',
}

export default function BulkStudentImportModal({ isOpen, onClose, onImported }) {
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
    // If anything was actually created, refresh the list on the way out.
    if (result?.created_count) onImported()
    reset()
    onClose()
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError('')
    setIsBusy(true)
    try {
      const data = await previewStudentImport(file)
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
      const complete = preview.records.filter((r) => r.is_complete)
      const data = await confirmStudentImport(
        complete.map((r) => ({
          full_name: r.full_name,
          father_name: r.father_name,
          enrollment_no: r.enrollment_no,
          seat_no: r.seat_no,
          email: r.email,
        })),
      )
      setResult(data)
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
          ? 'Upload an Excel or PDF roster. Nothing is created until you review and confirm.'
          : step === 'preview'
            ? 'Review the extracted records before adding them.'
            : 'Import complete.'
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
        <label htmlFor="roster-file" className="text-sm font-medium text-ink-700">
          Roster file
        </label>
        <input
          id="roster-file"
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
        <p className="text-xs text-ink-500">
          {Object.values(FIELD_LABELS).join(' · ')}
        </p>
        <p className="text-xs text-ink-500 mt-1.5">
          Column headings don't have to match exactly — they're matched by meaning, so
          "Guardian Name" or "Roll No" are understood. Passwords are generated automatically.
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
  const { total_detected, complete_count, incomplete_count, records, detected_columns, warnings } =
    preview

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <SummaryTile label="Students detected" value={total_detected} tone="neutral" />
        <SummaryTile label="Ready to add" value={complete_count} tone="success" />
        <SummaryTile label="Incomplete records" value={incomplete_count} tone="danger" />
      </div>

      {warnings.map((warning) => (
        <p
          key={warning}
          className="text-sm text-warning-700 bg-warning-50 rounded-lg px-3 py-2"
        >
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
                <TH>Father's Name</TH>
                <TH>Enrollment No</TH>
                <TH>Seat No</TH>
                <TH>Email</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {records.map((record) => (
                <TR key={record.row_number} className={record.is_complete ? '' : 'bg-danger-50/40'}>
                  <TD className="text-ink-500">{record.row_number}</TD>
                  <TD>{record.full_name ?? <Missing />}</TD>
                  <TD>{record.father_name ?? <Missing />}</TD>
                  <TD>{record.enrollment_no ?? <Missing />}</TD>
                  <TD>{record.seat_no ?? <Missing />}</TD>
                  <TD>{record.email ?? <Missing />}</TD>
                  <TD>
                    {record.is_complete ? (
                      <Badge tone="success">Ready</Badge>
                    ) : (
                      <span className="flex flex-col gap-1 items-start">
                        {record.missing_fields.length > 0 && (
                          <Badge tone="danger">Missing: {record.missing_fields.join(', ')}</Badge>
                        )}
                        {record.issues.map((issue) => (
                          <Badge key={issue} tone="warning">
                            {issue}
                          </Badge>
                        ))}
                      </span>
                    )}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </div>
      )}

      {incomplete_count > 0 && (
        <p className="text-xs text-ink-500">
          Incomplete records will not be added. Correct them in your file and upload again.
        </p>
      )}

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="button" onClick={onConfirm} isLoading={isBusy} disabled={complete_count === 0}>
          Add {complete_count} Student{complete_count === 1 ? '' : 's'}
        </Button>
      </ModalFooter>
    </div>
  )
}

function ResultStep({ result, onClose }) {
  const created = result.results.filter((r) => r.status === 'created')
  const skipped = result.results.filter((r) => r.status === 'skipped')

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <SummaryTile label="Students added" value={result.created_count} tone="success" />
        <SummaryTile label="Skipped" value={result.skipped_count} tone="danger" />
      </div>

      {created.length > 0 && (
        <div>
          <p className="text-sm font-medium text-ink-900 mb-1">Generated passwords</p>
          <p className="text-xs text-ink-500 mb-2">
            You can also see these later on each student's Edit page.
          </p>
          <div className="max-h-64 overflow-y-auto border border-border rounded-lg">
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Email</TH>
                  <TH>Enrollment No</TH>
                  <TH>Password</TH>
                </TR>
              </THead>
              <TBody>
                {created.map((row) => (
                  <TR key={row.email}>
                    <TD className="font-medium">{row.full_name}</TD>
                    <TD className="text-ink-500">{row.email}</TD>
                    <TD className="text-ink-500">{row.enrollment_no}</TD>
                    <TD className="font-mono text-xs">{row.generated_password}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        </div>
      )}

      {skipped.length > 0 && (
        <div>
          <p className="text-sm font-medium text-ink-900 mb-2">Skipped</p>
          <div className="max-h-40 overflow-y-auto border border-border rounded-lg">
            <Table>
              <THead>
                <TR>
                  <TH>Email</TH>
                  <TH>Reason</TH>
                </TR>
              </THead>
              <TBody>
                {skipped.map((row) => (
                  <TR key={row.email}>
                    <TD className="text-ink-500">{row.email}</TD>
                    <TD className="text-danger-600">{row.error}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        </div>
      )}

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
