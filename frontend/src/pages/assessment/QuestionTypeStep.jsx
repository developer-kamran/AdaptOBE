import { useState } from 'react'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import { QUESTION_TYPES } from './questionTypes'

// Entry dialog for "+ Add Question": pick a type, and for the bulk types
// (MCQ / Fill in the Blanks / True-False) also pick how many to create.
export default function QuestionTypeStep({ isOpen, onClose, onContinue }) {
  const [type, setType] = useState('question')
  const [quantity, setQuantity] = useState('5')

  const selected = QUESTION_TYPES.find((t) => t.value === type)

  function handleContinue() {
    if (selected.mode === 'bulk') {
      const n = Number(quantity)
      if (!Number.isInteger(n) || n < 1) return
      onContinue(type, n)
    } else {
      onContinue(type, 1)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Question" description="Choose a question type.">
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {QUESTION_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setType(t.value)}
              className={`rounded-lg border px-3 py-2.5 text-sm font-medium text-left transition-colors
                ${
                  type === t.value
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-border-strong text-ink-700 hover:border-brand-300'
                }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {selected.mode === 'bulk' && (
          <Input
            label="How many?"
            type="number"
            min="1"
            max="50"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        )}

        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" onClick={handleContinue}>
            Continue
          </Button>
        </ModalFooter>
      </div>
    </Modal>
  )
}
