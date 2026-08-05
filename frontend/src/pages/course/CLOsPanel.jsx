import { useEffect, useState } from 'react'
import { createClo, listClos } from '../../api/clos'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import MappingModal from './MappingModal'

export default function CLOsPanel({ course }) {
  const [clos, setClos] = useState(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [mappingClo, setMappingClo] = useState(null)

  const load = () => listClos(course.id).then(setClos)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course.id])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-500">Course Learning Outcomes for {course.code}.</p>
        <Button size="sm" onClick={() => setIsCreateOpen(true)}>
          + Add CLO
        </Button>
      </div>

      {clos === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : clos.length === 0 ? (
        <EmptyState
          title="No CLOs yet"
          description="Add a CLO, then map it to Programme Learning Outcomes using AI-suggested matches."
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Code</TH>
              <TH>Title</TH>
              <TH>Bloom Level</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {clos.map((clo) => (
              <TR key={clo.id}>
                <TD className="font-medium whitespace-nowrap">{clo.code}</TD>
                <TD>
                  <p className="font-medium text-ink-900">{clo.title}</p>
                  <p className="text-xs text-ink-500 mt-0.5 max-w-lg">{clo.description}</p>
                </TD>
                <TD className="text-ink-500">{clo.bloom_level || '—'}</TD>
                <TD>
                  <Button variant="secondary" size="sm" onClick={() => setMappingClo(clo)}>
                    Map to PLOs
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <CreateCloModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={load}
        courseId={course.id}
      />

      {mappingClo && (
        <MappingModal clo={mappingClo} onClose={() => setMappingClo(null)} />
      )}
    </div>
  )
}

function CreateCloModal({ isOpen, onClose, onCreated, courseId }) {
  const [code, setCode] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [bloomLevel, setBloomLevel] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setCode('')
    setTitle('')
    setDescription('')
    setBloomLevel('')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createClo(courseId, {
        code,
        title,
        description,
        bloom_level: bloomLevel || undefined,
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
    <Modal isOpen={isOpen} onClose={onClose} title="Add Course Learning Outcome">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Code"
          placeholder="CLO-1"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <Input
          label="Title"
          placeholder="Apply Design Patterns"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Textarea
          label="Description"
          placeholder="Design software components and select appropriate architectural patterns..."
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
        <Input
          label="Bloom Level (optional)"
          placeholder="Apply"
          value={bloomLevel}
          onChange={(e) => setBloomLevel(e.target.value)}
        />
        <p className="text-xs text-ink-500 -mt-2">
          A 384-dimensional embedding is generated automatically for AI-powered PLO mapping.
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
