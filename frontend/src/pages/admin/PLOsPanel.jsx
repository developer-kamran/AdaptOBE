import { useEffect, useState } from 'react'
import { listPrograms } from '../../api/admin'
import { createPlo, listPlos } from '../../api/plos'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function PLOsPanel() {
  const [programs, setPrograms] = useState([])
  const [selectedProgramId, setSelectedProgramId] = useState('')
  const [plos, setPlos] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    listPrograms().then((data) => {
      setPrograms(data)
      if (data.length > 0) setSelectedProgramId(String(data[0].id))
    })
  }, [])

  const load = () => {
    if (selectedProgramId) listPlos(Number(selectedProgramId)).then(setPlos)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProgramId])

  return (
    <div>
      <div className="flex items-center justify-between mb-4 gap-3">
        <div className="w-64">
          <Select value={selectedProgramId} onChange={(e) => setSelectedProgramId(e.target.value)}>
            {programs.map((program) => (
              <option key={program.id} value={program.id}>
                {program.code} — {program.name}
              </option>
            ))}
          </Select>
        </div>
        <Button size="sm" onClick={() => setIsModalOpen(true)} disabled={!selectedProgramId}>
          + Add PLO
        </Button>
      </div>

      {plos === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : plos.length === 0 ? (
        <EmptyState title="No PLOs for this programme yet" description="Add one to get started." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Code</TH>
              <TH>Title</TH>
              <TH>Domain</TH>
            </TR>
          </THead>
          <TBody>
            {plos.map((plo) => (
              <TR key={plo.id}>
                <TD className="font-medium whitespace-nowrap">{plo.code}</TD>
                <TD>
                  <p className="font-medium text-ink-900">{plo.title}</p>
                  <p className="text-xs text-ink-500 mt-0.5 max-w-xl">{plo.description}</p>
                </TD>
                <TD>{plo.domain && <Badge tone="brand">{plo.domain}</Badge>}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <CreatePloModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={load}
        programId={selectedProgramId}
      />
    </div>
  )
}

function CreatePloModal({ isOpen, onClose, onCreated, programId }) {
  const [code, setCode] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [domain, setDomain] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setCode('')
    setTitle('')
    setDescription('')
    setDomain('')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createPlo({
        program_id: Number(programId),
        code,
        title,
        description,
        domain: domain || undefined,
      })
      reset()
      onClose()
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Programme Learning Outcome">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Code"
          placeholder="PLO-1"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <Input
          label="Title"
          placeholder="Engineering Knowledge"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Textarea
          label="Description"
          placeholder="Apply knowledge of mathematics, science and engineering fundamentals..."
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
        <Input
          label="Bloom Domain (optional)"
          placeholder="Cognitive"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
        />
        <p className="text-xs text-ink-500 -mt-2">
          A 384-dimensional embedding is generated automatically for AI-powered CLO mapping.
        </p>
        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
