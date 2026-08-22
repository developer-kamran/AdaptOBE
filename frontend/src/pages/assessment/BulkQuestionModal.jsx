import { useEffect, useState } from 'react'
import { createQuestionsBulk, suggestQuestionTag } from '../../api/assessments'
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

// Creates `quantity` items of one bulk type (MCQ / Fill in the Blanks /
// True-False) in a single request, all-or-nothing.
export default function BulkQuestionModal({
  isOpen,
  onClose,
  onSaved,
  assessmentId,
  clos,
  nextNumber,
  type,
  quantity,
  remainingMarks,
  existingNumbers,
}) {
  const [items, setItems] = useState([])
  const [suggestions, setSuggestions] = useState([]) // suggestions[index] -> array | null
  const [suggestingIndex, setSuggestingIndex] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    setItems(
      Array.from({ length: quantity }, (_, i) => ({
        question_number: nextNumber + i,
        marks: '5',
        text: '',
        clo_id: '',
        type_data: emptyTypeData(type),
      })),
    )
    setSuggestions(Array.from({ length: quantity }, () => null))
    setError('')
  }, [isOpen, quantity, nextNumber, type])

  function updateItem(index, patch) {
    setItems((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  async function handleSuggest(index) {
    const text = items[index]?.text
    if (!text?.trim()) return
    setSuggestingIndex(index)
    try {
      const result = await suggestQuestionTag(assessmentId, text)
      setSuggestions((current) => current.map((s, i) => (i === index ? result.suggestions : s)))
    } catch {
      setSuggestions((current) => current.map((s, i) => (i === index ? [] : s)))
    } finally {
      setSuggestingIndex(null)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const numbers = items.map((i) => Number(i.question_number))
    const numberSet = new Set(numbers)
    if (numberSet.size !== numbers.length) {
      setError('Question numbers must be unique across these items.')
      return
    }
    if (existingNumbers && numbers.some((n) => existingNumbers.has(n))) {
      setError('One of these question numbers already exists in this assessment.')
      return
    }
    if (items.some((i) => Number(i.marks) <= 0)) {
      setError('Every item must have marks greater than 0.')
      return
    }
    const totalMarks = items.reduce((sum, i) => sum + Number(i.marks || 0), 0)
    if (remainingMarks != null && totalMarks > remainingMarks) {
      setError(`These items total ${totalMarks} marks, which exceeds the ${remainingMarks} remaining.`)
      return
    }

    setIsSubmitting(true)
    try {
      await createQuestionsBulk(
        assessmentId,
        items.map((item) => ({
          question_number: Number(item.question_number),
          marks: Number(item.marks),
          clo_id: item.clo_id ? Number(item.clo_id) : null,
          text: item.text,
          question_type: type,
          type_data: item.type_data,
        })),
      )
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
      width="max-w-3xl"
      title={`Add ${quantity} ${QUESTION_TYPE_LABEL[type]} Item${quantity === 1 ? '' : 's'}`}
      description="Fill in each item, then create them all at once."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="max-h-[55vh] overflow-y-auto flex flex-col gap-4 pr-1">
          {items.map((item, index) => (
            <div key={index} className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold text-ink-500 uppercase tracking-wide mb-2">
                Item {index + 1}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <Input
                  label="Question #"
                  type="number"
                  min="1"
                  value={item.question_number}
                  onChange={(e) => updateItem(index, { question_number: e.target.value })}
                  required
                />
                <Input
                  label="Marks"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={item.marks}
                  onChange={(e) => updateItem(index, { marks: e.target.value })}
                  required
                />
              </div>
              <TypeFieldsEditor
                type={type}
                text={item.text}
                onTextChange={(text) => updateItem(index, { text })}
                typeData={item.type_data}
                onTypeDataChange={(type_data) => updateItem(index, { type_data })}
              />
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-ink-700">CLO Tag</label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSuggest(index)}
                    isLoading={suggestingIndex === index}
                    disabled={!item.text?.trim()}
                  >
                    Suggest with AI
                  </Button>
                </div>
                <Select
                  value={item.clo_id}
                  onChange={(e) => updateItem(index, { clo_id: e.target.value })}
                  required
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
                          onClick={() => updateItem(index, { clo_id: String(s.clo_id) })}
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
                      AI compared this question's wording with each CLO using semantic similarity,
                      then labels the match Strong, Moderate, or Weak based on that score.
                    </InfoTooltip>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create {quantity} Item{quantity === 1 ? '' : 's'}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
