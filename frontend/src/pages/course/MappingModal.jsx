import { useEffect, useMemo, useState } from 'react'
import { listPlos } from '../../api/plos'
import { confirmMapping, deleteMapping, listMappingsForClo, suggestMappings } from '../../api/mappings'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'

const STRENGTH_LABEL = { 1: 'Weak', 2: 'Moderate', 3: 'Strong' }

// A sensible default strength from cosine similarity, so faculty aren't stuck
// picking a number blind -- they can still override it before confirming.
function strengthFromSimilarity(score) {
  if (score >= 0.5) return 3
  if (score >= 0.3) return 2
  return 1
}

export default function MappingModal({ clo, onClose }) {
  const [ploLookup, setPloLookup] = useState(null)
  const [confirmed, setConfirmed] = useState(null)
  const [suggestions, setSuggestions] = useState(null)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [confirmingPloId, setConfirmingPloId] = useState(null)
  const [error, setError] = useState('')

  const loadConfirmed = () => listMappingsForClo(clo.id).then(setConfirmed)

  useEffect(() => {
    listPlos().then((all) => {
      setPloLookup(new Map(all.map((plo) => [plo.id, plo])))
    })
    loadConfirmed()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clo.id])

  const confirmedPloIds = useMemo(
    () => new Set((confirmed ?? []).map((m) => m.plo_id)),
    [confirmed],
  )

  async function handleSuggest() {
    setError('')
    setIsSuggesting(true)
    try {
      const result = await suggestMappings(clo.id, 5)
      setSuggestions(result.suggestions)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not fetch suggestions.')
    } finally {
      setIsSuggesting(false)
    }
  }

  async function handleConfirm(suggestion, strength) {
    setConfirmingPloId(suggestion.plo_id)
    setError('')
    try {
      await confirmMapping({
        clo_id: clo.id,
        plo_id: suggestion.plo_id,
        strength,
        is_ai_generated: true,
        similarity_score: suggestion.similarity_score,
      })
      await loadConfirmed()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not confirm mapping.')
    } finally {
      setConfirmingPloId(null)
    }
  }

  async function handleDelete(mappingId) {
    await deleteMapping(mappingId)
    loadConfirmed()
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={`Map "${clo.code}" to Programme Learning Outcomes`}
      description={clo.title}
      width="max-w-2xl"
    >
      <div className="flex flex-col gap-6">
        <section>
          <h3 className="text-xs font-semibold text-ink-500 uppercase tracking-wide mb-2">
            Confirmed Mappings
          </h3>
          {confirmed === null ? (
            <Spinner className="h-4 w-4" />
          ) : confirmed.length === 0 ? (
            <p className="text-sm text-ink-400">No PLOs mapped yet.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {confirmed.map((mapping) => {
                const plo = ploLookup?.get(mapping.plo_id)
                return (
                  <div
                    key={mapping.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink-900">
                        {plo?.code ?? `PLO #${mapping.plo_id}`} — {plo?.title}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <Badge tone="brand">{STRENGTH_LABEL[mapping.strength]}</Badge>
                        {mapping.is_ai_generated && <Badge tone="neutral">AI-suggested</Badge>}
                        {mapping.similarity_score != null && (
                          <span className="text-xs text-ink-400">
                            similarity {mapping.similarity_score.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(mapping.id)}>
                      Remove
                    </Button>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-ink-500 uppercase tracking-wide">
              AI-Suggested Matches
            </h3>
            <Button variant="secondary" size="sm" onClick={handleSuggest} isLoading={isSuggesting}>
              {suggestions ? 'Refresh Suggestions' : 'Get AI Suggestions'}
            </Button>
          </div>

          {suggestions && (
            <div className="flex flex-col gap-2">
              {suggestions
                .filter((s) => !confirmedPloIds.has(s.plo_id))
                .map((suggestion) => (
                  <div
                    key={suggestion.plo_id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 bg-slate-50"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink-900">
                        {suggestion.code} — {suggestion.title}
                      </p>
                      <p className="text-xs text-ink-500 mt-0.5">
                        cosine similarity{' '}
                        <span className="font-mono font-medium text-brand-700">
                          {suggestion.similarity_score.toFixed(3)}
                        </span>
                      </p>
                    </div>
                    <Button
                      size="sm"
                      isLoading={confirmingPloId === suggestion.plo_id}
                      onClick={() =>
                        handleConfirm(suggestion, strengthFromSimilarity(suggestion.similarity_score))
                      }
                    >
                      Confirm as {STRENGTH_LABEL[strengthFromSimilarity(suggestion.similarity_score)]}
                    </Button>
                  </div>
                ))}
              {suggestions.filter((s) => !confirmedPloIds.has(s.plo_id)).length === 0 && (
                <p className="text-sm text-ink-400">All top suggestions are already confirmed.</p>
              )}
            </div>
          )}
        </section>

        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
      </div>
    </Modal>
  )
}
