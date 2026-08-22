import { useEffect, useState } from 'react'
import { createClo, generateCloSuggestion } from '../../api/clos'
import { listPlos } from '../../api/plos'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import Select from '../../components/ui/Select'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'

const BLOOM_LEVELS = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']

// A separate flow from MappingModal (which maps an *existing* CLO to PLOs by
// similarity). This one generates the wording for a brand-new CLO from a
// topic/target-PLO/requirements via a real LLM call -- nothing is ever saved
// until the faculty reviews the suggestion and explicitly clicks "Add CLO".
export default function AiCloModal({ isOpen, onClose, onSaved, course }) {
  const [plos, setPlos] = useState(null)
  const [selectedPloIds, setSelectedPloIds] = useState([])
  const [topic, setTopic] = useState('')
  const [requirements, setRequirements] = useState('')
  const [suggestion, setSuggestion] = useState(null) // { code, title, description, bloom_level }
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isOpen) return
    setSelectedPloIds([])
    setTopic('')
    setRequirements('')
    setSuggestion(null)
    setError('')
    listPlos(course.program_id).then(setPlos)
  }, [isOpen, course.program_id])

  function togglePlo(id) {
    setSelectedPloIds((current) =>
      current.includes(id) ? current.filter((p) => p !== id) : [...current, id],
    )
  }

  async function handleGenerate(e) {
    e.preventDefault()
    setError('')
    if (selectedPloIds.length === 0) {
      setError('Select at least one target PLO.')
      return
    }
    setIsGenerating(true)
    try {
      const result = await generateCloSuggestion(course.id, {
        target_plo_ids: selectedPloIds,
        topic,
        requirements,
      })
      setSuggestion({ code: '', ...result })
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not generate a CLO right now.')
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleAdd(e) {
    e.preventDefault()
    setError('')
    if (!suggestion.code.trim()) {
      setError('Give this CLO a code before adding it.')
      return
    }
    setIsSaving(true)
    try {
      await createClo(course.id, {
        code: suggestion.code,
        title: suggestion.title,
        description: suggestion.description,
        bloom_level: suggestion.bloom_level,
      })
      onClose()
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} width="max-w-xl" title="Create CLO with AI">
      {!suggestion ? (
        <form onSubmit={handleGenerate} className="flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium text-ink-700 mb-1.5 block">Target PLO(s)</label>
            {plos === null ? (
              <div className="flex justify-center py-4">
                <Spinner />
              </div>
            ) : (
              <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto border border-border rounded-lg p-2.5">
                {plos.map((plo) => (
                  <label key={plo.id} className="flex items-start gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPloIds.includes(plo.id)}
                      onChange={() => togglePlo(plo.id)}
                      className="mt-0.5 h-4 w-4 text-brand-600 rounded focus:ring-brand-500"
                    />
                    <span>
                      <span className="font-medium">{plo.code}</span> — {plo.title}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
          <Input
            label="Topic / Concept"
            placeholder="CPU Scheduling"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
          />
          <Textarea
            label="Additional Requirements (optional)"
            placeholder="Keep it to one sentence, focus on FCFS and Round Robin..."
            rows={3}
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
          />
          {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
          <ModalFooter>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isGenerating}>
              Generate
            </Button>
          </ModalFooter>
        </form>
      ) : (
        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          <p className="text-xs text-ink-500 -mt-1">
            Review and edit the AI's suggestion before adding it — nothing is saved yet.
          </p>
          <Input
            label="Code"
            placeholder="CLO-4"
            value={suggestion.code}
            onChange={(e) => setSuggestion({ ...suggestion, code: e.target.value })}
            required
          />
          <Input
            label="Title"
            value={suggestion.title}
            onChange={(e) => setSuggestion({ ...suggestion, title: e.target.value })}
            required
          />
          <Textarea
            label="Description"
            rows={3}
            value={suggestion.description}
            onChange={(e) => setSuggestion({ ...suggestion, description: e.target.value })}
            required
          />
          <Select
            label="Bloom Level"
            value={suggestion.bloom_level}
            onChange={(e) => setSuggestion({ ...suggestion, bloom_level: e.target.value })}
            required
          >
            {BLOOM_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </Select>
          {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
          <ModalFooter>
            <Button type="button" variant="secondary" onClick={() => setSuggestion(null)}>
              Back
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Add CLO
            </Button>
          </ModalFooter>
        </form>
      )}
    </Modal>
  )
}
