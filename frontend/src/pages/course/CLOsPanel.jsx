import { useEffect, useState } from 'react'
import { DndContext, closestCenter } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { createClo, deleteClo, listClos, updateClo } from '../../api/clos'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import Select from '../../components/ui/Select'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import SortableRow from '../../components/ui/SortableRow'
import DragHandle from '../../components/ui/DragHandle'
import useLocalOrder from '../../hooks/useLocalOrder'
import useDndSensors from '../../hooks/useDndSensors'
import MappingModal from './MappingModal'
import AiCloModal from './AiCloModal'

//: Standard Bloom's Taxonomy (cognitive domain) levels -- must match
//: `BLOOM_LEVELS` in `backend/app/schemas/clo.py`.
const BLOOM_LEVELS = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']

export default function CLOsPanel({ course }) {
  const [clos, setClos] = useState(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isAiCreateOpen, setIsAiCreateOpen] = useState(false)
  const [editingClo, setEditingClo] = useState(null)
  const [mappingClo, setMappingClo] = useState(null)
  const [error, setError] = useState('')

  const { applyOrder, reorder } = useLocalOrder(`adaptobe.clo-order.${course.id}`)
  const sensors = useDndSensors()
  const orderedClos = clos ? applyOrder(clos) : clos

  const load = () => listClos(course.id).then(setClos)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course.id])

  function handleDragEnd(event) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    reorder(orderedClos, active.id, over.id)
  }

  async function handleDelete(clo) {
    if (!window.confirm(`Delete CLO "${clo.code}"? This also removes its PLO mappings.`)) return
    setError('')
    try {
      await deleteClo(clo.id)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Course Learning Outcomes for {course.code}.</p>
        <div className="flex flex-wrap gap-2 self-start sm:self-auto">
          <Button variant="secondary" size="sm" onClick={() => setIsAiCreateOpen(true)}>
            Create CLO with AI
          </Button>
          <Button size="sm" onClick={() => setIsCreateOpen(true)}>
            + Add CLO
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

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
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={orderedClos.map((c) => c.id)} strategy={verticalListSortingStrategy}>
            <Table>
              <THead>
                <TR>
                  <TH className="w-8"></TH>
                  <TH>Code</TH>
                  <TH>Title</TH>
                  <TH>Bloom Level</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {orderedClos.map((clo) => (
                  <SortableRow key={clo.id} id={clo.id}>
                    {({ attributes, listeners }) => (
                      <>
                        <TD>
                          <DragHandle attributes={attributes} listeners={listeners} />
                        </TD>
                        <TD className="font-medium whitespace-nowrap">{clo.code}</TD>
                        <TD>
                          <p className="font-medium text-ink-900">{clo.title}</p>
                          <p className="text-xs text-ink-500 mt-0.5 max-w-lg">{clo.description}</p>
                        </TD>
                        <TD className="text-ink-500">{clo.bloom_level || '—'}</TD>
                        <TD>
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="secondary" size="sm" onClick={() => setMappingClo(clo)}>
                              Map to PLOs
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setEditingClo(clo)}>
                              Edit
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(clo)}>
                              Delete
                            </Button>
                          </div>
                        </TD>
                      </>
                    )}
                  </SortableRow>
                ))}
              </TBody>
            </Table>
          </SortableContext>
        </DndContext>
      )}

      <CloFormModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSaved={load}
        courseId={course.id}
        mode="create"
      />
      <CloFormModal
        isOpen={editingClo !== null}
        onClose={() => setEditingClo(null)}
        onSaved={load}
        courseId={course.id}
        mode="edit"
        clo={editingClo}
      />

      {mappingClo && (
        <MappingModal clo={mappingClo} onClose={() => setMappingClo(null)} />
      )}

      <AiCloModal
        isOpen={isAiCreateOpen}
        onClose={() => setIsAiCreateOpen(false)}
        onSaved={load}
        course={course}
      />
    </div>
  )
}

function CloFormModal({ isOpen, onClose, onSaved, courseId, mode, clo }) {
  const [code, setCode] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [bloomLevel, setBloomLevel] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setCode(clo?.code ?? '')
      setTitle(clo?.title ?? '')
      setDescription(clo?.description ?? '')
      setBloomLevel(clo?.bloom_level ?? '')
      setError('')
    }
  }, [isOpen, clo])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const data = { code, title, description, bloom_level: bloomLevel }
      if (mode === 'edit') {
        await updateClo(clo.id, data)
      } else {
        await createClo(courseId, data)
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
      title={mode === 'edit' ? 'Edit Course Learning Outcome' : 'Add Course Learning Outcome'}
    >
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
        <Select
          label="Bloom Level"
          value={bloomLevel}
          onChange={(e) => setBloomLevel(e.target.value)}
          required
        >
          <option value="" disabled>
            Select a Bloom level…
          </option>
          {BLOOM_LEVELS.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </Select>
        <p className="text-xs text-ink-500 -mt-2">
          A 384-dimensional embedding is generated automatically for AI-powered PLO mapping.
        </p>
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
