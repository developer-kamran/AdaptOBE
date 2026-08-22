import { useState } from 'react'
import { createQuestionsBulk, previewPaperImport, suggestQuestionTag } from '../../api/assessments'
import { ApiError } from '../../api/client'
import { similarityLabel } from '../../utils/similarity'
import Button from '../../components/ui/Button'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import InfoTooltip from '../../components/ui/InfoTooltip'
import TypeFieldsEditor from './TypeFieldsEditor'
import { QUESTION_TYPE_LABEL } from './questionTypes'

const VERIFICATION_FIELDS = [
  { key: 'assessment_title', label: 'Assessment Title' },
  { key: 'course_name', label: 'Course' },
  { key: 'course_code', label: 'Course Code' },
  { key: 'instructor', label: 'Instructor' },
]

// Upload -> Extract -> Verify assessment details -> Preview extracted
// questions -> Faculty confirmation -> Add questions. Verification and
// extraction both happen server-side in one preview call; nothing is saved
// until the faculty explicitly confirms, and confirming reuses the same
// bulk question-create endpoint the manual "+ Add Question" bulk flow uses
// -- no parallel write path.
export default function PaperImportModal({
  isOpen,
  onClose,
  onImported,
  assessmentId,
  clos,
  nextNumber,
  remainingMarks,
}) {
  const [step, setStep] = useState('upload') // upload | preview | result
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [items, setItems] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [suggestingIndex, setSuggestingIndex] = useState(null)
  const [acknowledgeMismatch, setAcknowledgeMismatch] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isBusy, setIsBusy] = useState(false)

  function reset() {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setItems([])
    setSuggestions([])
    setAcknowledgeMismatch(false)
    setResult(null)
    setError('')
    setIsBusy(false)
  }

  function handleClose() {
    if (result?.created) onImported()
    reset()
    onClose()
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError('')
    setIsBusy(true)
    try {
      const data = await previewPaperImport(assessmentId, file)
      setPreview(data)
      setItems(
        data.questions.map((q) => ({
          include: true,
          question_type: q.question_type,
          text: q.text,
          marks: q.marks != null ? String(q.marks) : '',
          // Pre-filled only when the document itself tagged a CLO next to
          // this question and it matched one of this course's real CLOs --
          // still just a starting point, never final: the manual Select
          // and "Suggest with AI" below remain fully editable either way.
          clo_id: q.clo_id != null ? String(q.clo_id) : '',
          cloDetectedFromDocument: q.clo_id != null,
          type_data: q.type_data,
        })),
      )
      setSuggestions(data.questions.map(() => null))
      setAcknowledgeMismatch(false)
      setStep('preview')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not read that file.')
    } finally {
      setIsBusy(false)
    }
  }

  function updateItem(index, patch) {
    setItems((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  async function handleSuggest(index) {
    const text = items[index]?.text
    if (!text?.trim()) return
    setSuggestingIndex(index)
    try {
      const res = await suggestQuestionTag(assessmentId, text)
      setSuggestions((current) => current.map((s, i) => (i === index ? res.suggestions : s)))
    } catch {
      setSuggestions((current) => current.map((s, i) => (i === index ? [] : s)))
    } finally {
      setSuggestingIndex(null)
    }
  }

  const includedItems = items.filter((item) => item.include)
  const requiresAcknowledgement = preview ? !preview.verification.all_matched : false
  const canConfirm = includedItems.length > 0 && (!requiresAcknowledgement || acknowledgeMismatch)

  async function handleConfirm() {
    setError('')
    if (includedItems.length === 0) {
      setError('Select at least one question to import.')
      return
    }
    if (includedItems.some((item) => !item.text?.trim())) {
      setError('Every selected question needs text.')
      return
    }
    if (includedItems.some((item) => Number(item.marks) <= 0 || item.marks === '')) {
      setError('Every selected question needs marks greater than 0.')
      return
    }
    const totalMarks = includedItems.reduce((sum, item) => sum + Number(item.marks || 0), 0)
    if (remainingMarks != null && totalMarks > remainingMarks) {
      setError(`Selected questions total ${totalMarks} marks, which exceeds the ${remainingMarks} remaining.`)
      return
    }

    setIsBusy(true)
    try {
      const payload = includedItems.map((item, i) => ({
        question_number: nextNumber + i,
        marks: Number(item.marks),
        clo_id: item.clo_id ? Number(item.clo_id) : null,
        text: item.text,
        question_type: item.question_type,
        // Tags the created question as having come from this upload flow
        // (rather than manual entry) so the Questions table can show an
        // "Extracted" badge -- reuses the existing flexible `type_data`
        // JSONB column, no schema change needed.
        type_data: { ...(item.type_data || {}), source: 'paper_import' },
      }))
      const response = await createQuestionsBulk(assessmentId, payload)
      setResult({ created: response.created.length })
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
      width="max-w-4xl"
      title="Upload Assessment Paper"
      description={
        step === 'upload'
          ? 'Upload the actual Quiz/Assignment/Exam paper -- questions are extracted automatically.'
          : step === 'preview'
            ? 'Review the extracted details and questions before anything is added.'
            : 'Questions added.'
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
          items={items}
          updateItem={updateItem}
          suggestions={suggestions}
          suggestingIndex={suggestingIndex}
          onSuggest={handleSuggest}
          clos={clos}
          acknowledgeMismatch={acknowledgeMismatch}
          setAcknowledgeMismatch={setAcknowledgeMismatch}
          requiresAcknowledgement={requiresAcknowledgement}
          includedCount={includedItems.length}
          canConfirm={canConfirm}
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
        <label htmlFor="assessment-paper-file" className="text-sm font-medium text-ink-700">
          Assessment paper
        </label>
        <input
          id="assessment-paper-file"
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-ink-700 file:mr-3 file:rounded-lg file:border-0
            file:bg-brand-600 file:px-3 file:py-2 file:text-sm file:font-medium
            file:text-white hover:file:bg-brand-700"
          required
        />
      </div>

      <div className="rounded-lg bg-slate-50 border border-border px-3 py-2.5">
        <p className="text-xs font-medium text-ink-700 mb-1">
          Upload the real paper for this assessment (PDF or Word) -- Normal, MCQ, Fill in the
          Blank, and True/False questions are detected automatically.
        </p>
        <p className="text-xs text-ink-500">
          The document's Assessment Title, Course, Course Code, and Instructor are checked
          against this assessment before anything can be imported. Nothing is saved until you
          review and confirm on the next screen.
        </p>
      </div>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isBusy} disabled={!file}>
          Extract Questions
        </Button>
      </ModalFooter>
    </form>
  )
}

function PreviewStep({
  preview,
  items,
  updateItem,
  suggestions,
  suggestingIndex,
  onSuggest,
  clos,
  acknowledgeMismatch,
  setAcknowledgeMismatch,
  requiresAcknowledgement,
  includedCount,
  canConfirm,
  isBusy,
  onConfirm,
  onBack,
}) {
  return (
    <div className="flex flex-col gap-4">
      <VerificationCard verification={preview.verification} />

      {preview.warnings.map((warning) => (
        <p key={warning} className="text-sm text-warning-700 bg-warning-50 rounded-lg px-3 py-2">
          {warning}
        </p>
      ))}

      {requiresAcknowledgement && (
        <label className="flex items-start gap-2 text-sm text-danger-700 bg-danger-50 rounded-lg px-3 py-2.5">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={acknowledgeMismatch}
            onChange={(e) => setAcknowledgeMismatch(e.target.checked)}
          />
          <span>
            I've checked this document and confirm it's the right one for this assessment -- import
            anyway.
          </span>
        </label>
      )}

      {items.length === 0 ? (
        <p className="text-sm text-ink-500 py-6 text-center">
          No questions could be extracted from this document.
        </p>
      ) : (
        <div className="max-h-[45vh] overflow-y-auto flex flex-col gap-3 pr-1">
          {items.map((item, index) => (
            <div key={index} className={`rounded-lg border p-3 ${item.include ? 'border-border' : 'border-border bg-slate-50/60 opacity-60'}`}>
              <div className="flex items-center justify-between mb-2">
                <label className="flex items-center gap-2 text-xs font-semibold text-ink-500 uppercase tracking-wide">
                  <input
                    type="checkbox"
                    checked={item.include}
                    onChange={(e) => updateItem(index, { include: e.target.checked })}
                  />
                  Question {index + 1}
                </label>
                <Badge tone="neutral">{QUESTION_TYPE_LABEL[item.question_type] ?? item.question_type}</Badge>
              </div>

              <fieldset disabled={!item.include} className="flex flex-col gap-3">
                <Input
                  label="Marks"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={item.marks}
                  onChange={(e) => updateItem(index, { marks: e.target.value })}
                  className="max-w-[10rem]"
                  required
                />
                <TypeFieldsEditor
                  type={item.question_type}
                  text={item.text}
                  onTextChange={(text) => updateItem(index, { text })}
                  typeData={item.type_data}
                  onTypeDataChange={(type_data) => updateItem(index, { type_data })}
                />
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="flex items-center gap-1.5">
                      <label className="text-sm font-medium text-ink-700">CLO Tag</label>
                      {item.cloDetectedFromDocument && (
                        <Badge tone="brand">Detected from document</Badge>
                      )}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => onSuggest(index)}
                      isLoading={suggestingIndex === index}
                      disabled={!item.text?.trim()}
                    >
                      Suggest with AI
                    </Button>
                  </div>
                  <Select
                    value={item.clo_id}
                    onChange={(e) =>
                      updateItem(index, { clo_id: e.target.value, cloDetectedFromDocument: false })
                    }
                  >
                    <option value="">— Untagged —</option>
                    {clos.map((clo) => (
                      <option key={clo.id} value={clo.id}>
                        {clo.code} — {clo.title}
                      </option>
                    ))}
                  </Select>
                  {suggestions[index] && suggestions[index].length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      {suggestions[index].map((s) => {
                        const { label, tone } = similarityLabel(s.similarity_score)
                        const isSelected = item.clo_id === String(s.clo_id)
                        return (
                          <button
                            key={s.clo_id}
                            type="button"
                            onClick={() =>
                              updateItem(index, { clo_id: String(s.clo_id), cloDetectedFromDocument: false })
                            }
                            className={`text-xs rounded-full px-2.5 py-1 border transition-colors
                              ${
                                isSelected
                                  ? 'bg-brand-600 text-white border-brand-600'
                                  : 'bg-white text-ink-700 border-border-strong hover:border-brand-400'
                              }`}
                          >
                            {s.code} · <Badge tone={isSelected ? 'neutral' : tone}>{label}</Badge>
                          </button>
                        )
                      })}
                      <InfoTooltip>
                        AI compared this question's wording with each CLO using semantic
                        similarity, then labels the match Strong, Moderate, or Weak.
                      </InfoTooltip>
                    </div>
                  )}
                </div>
              </fieldset>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-ink-500">
        Unchecked questions are left out. Question numbers are assigned automatically, continuing
        from this assessment's existing questions.
      </p>

      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="button" onClick={onConfirm} isLoading={isBusy} disabled={!canConfirm}>
          Add {includedCount} Question{includedCount === 1 ? '' : 's'}
        </Button>
      </ModalFooter>
    </div>
  )
}

function VerificationCard({ verification }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs font-semibold text-ink-500 uppercase tracking-wide mb-2">
        Document Verification
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {VERIFICATION_FIELDS.map(({ key, label }) => {
          const field = verification[key]
          return (
            <div
              key={key}
              className={`rounded-md border px-2.5 py-2 text-xs ${
                field.matches ? 'border-green-200 bg-success-50' : 'border-red-200 bg-danger-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink-700">{label}</span>
                <span className={field.matches ? 'text-success-700' : 'text-danger-700'}>
                  {field.matches ? '✓ Match' : '✗ Mismatch'}
                </span>
              </div>
              <p className="mt-1 text-ink-500">
                Found: {field.detected ?? <span className="italic">not detected</span>}
              </p>
              <p className="text-ink-500">Expected: {field.expected}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ResultStep({ result, onClose }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-green-200 bg-success-50 px-3 py-2.5">
        <p className="text-xl font-semibold leading-tight text-success-700">{result.created}</p>
        <p className="text-xs mt-0.5 text-success-700 opacity-80">
          Question{result.created === 1 ? '' : 's'} added
        </p>
      </div>
      <ModalFooter>
        <Button type="button" onClick={onClose}>
          Done
        </Button>
      </ModalFooter>
    </div>
  )
}
