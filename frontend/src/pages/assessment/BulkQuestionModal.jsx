import { useEffect, useState } from 'react'
import { createQuestionsBulk } from '../../api/assessments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Modal, { ModalFooter } from '../../components/ui/Modal'
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
    setError('')
  }, [isOpen, quantity, nextNumber, type])

  function updateItem(index, patch) {
    setItems((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)))
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
                  min="0"
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
                <Select
                  label="CLO Tag"
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
