import { useEffect, useState } from 'react'
import { createQuestion, suggestQuestionTag, updateQuestion } from '../../api/assessments'
import { ApiError } from '../../api/client'
import { similarityLabel } from '../../utils/similarity'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import InfoTooltip from '../../components/ui/InfoTooltip'
import TypeFieldsEditor from './TypeFieldsEditor'
import { QUESTION_TYPE_LABEL, emptyTypeData } from './questionTypes'

// Create (for the single-item types: Question/Project/Lab) or edit (for any
// type -- editing an MCQ/Fill-in-the-Blank/True-False item happens one at a
// time here too, even though it was created in a batch).
export default function QuestionFormModal({
  isOpen,
  onClose,
  onSaved,
  assessmentId,
  clos,
  nextNumber,
  mode,
  type,
  question,
  remainingMarks,
  existingNumbers,
}) {
  const [questionNumber, setQuestionNumber] = useState(nextNumber)
  const [marks, setMarks] = useState('10')
  const [text, setText] = useState('')
  const [typeData, setTypeData] = useState(null)
  const [cloId, setCloId] = useState('')
  const [suggestions, setSuggestions] = useState(null)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const effectiveType = mode === 'edit' ? question?.question_type : type

  useEffect(() => {
    if (!isOpen) return
    if (mode === 'edit' && question) {
      setQuestionNumber(question.question_number)
      setMarks(String(question.marks))
      setText(question.text ?? '')
      setTypeData(question.type_data ?? emptyTypeData(question.question_type))
      setCloId(question.clo_id ? String(question.clo_id) : '')
    } else {
      setQuestionNumber(nextNumber)
      setMarks('10')
      setText('')
      setTypeData(emptyTypeData(type))
      setCloId('')
    }
    setSuggestions(null)
    setError('')
  }, [isOpen, mode, question, type, nextNumber])

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

    const numberTaken = existingNumbers?.has(Number(questionNumber)) && (mode === 'create' || Number(questionNumber) !== question.question_number)
    if (numberTaken) {
      setError(`Question number ${questionNumber} already exists in this assessment.`)
      return
    }
    if (remainingMarks != null && Number(marks) > remainingMarks) {
      setError(`Marks would exceed the assessment's total by ${(Number(marks) - remainingMarks).toFixed(2)}.`)
      return
    }

    setIsSubmitting(true)
    try {
      const payload = {
        question_number: Number(questionNumber),
        marks: Number(marks),
        clo_id: cloId ? Number(cloId) : null,
        text,
        question_type: effectiveType,
        type_data: typeData,
      }
      if (mode === 'edit') {
        await updateQuestion(question.id, payload)
      } else {
        await createQuestion(assessmentId, payload)
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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        mode === 'edit'
          ? `Edit ${QUESTION_TYPE_LABEL[effectiveType] ?? 'Question'}`
          : `Add ${QUESTION_TYPE_LABEL[effectiveType] ?? 'Question'}`
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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

        <TypeFieldsEditor
          type={effectiveType}
          text={text}
          onTextChange={setText}
          typeData={typeData}
          onTypeDataChange={setTypeData}
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
          <Select value={cloId} onChange={(e) => setCloId(e.target.value)} required>
            <option value="">— Untagged —</option>
            {clos.map((clo) => (
              <option key={clo.id} value={clo.id}>
                {clo.code} — {clo.title}
              </option>
            ))}
          </Select>

          {suggestions && suggestions.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              {suggestions.map((s) => {
                const { label, tone } = similarityLabel(s.similarity_score)
                return (
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
                    {s.code} · <Badge tone={cloId === String(s.clo_id) ? 'neutral' : tone}>{label}</Badge>
                  </button>
                )
              })}
              <InfoTooltip>
                AI compared this question's wording with each CLO using semantic similarity,
                then labels the match Strong, Moderate, or Weak based on that score.
              </InfoTooltip>
            </div>
          )}
        </div>

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
