import { useEffect, useState } from 'react'
import { createProgram, deleteProgram, listPrograms, updateProgram } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function ProgramsPanel() {
  const [programs, setPrograms] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')

  const load = () => listPrograms().then(setPrograms)

  useEffect(() => {
    load()
  }, [])

  async function handleDelete(program) {
    if (!window.confirm(`Delete programme "${program.name}"? This cannot be undone.`)) return
    setError('')
    try {
      await deleteProgram(program.id)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Degree programmes in your department.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
          + Add Programme
        </Button>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {programs === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : programs.length === 0 ? (
        <EmptyState title="No programmes yet" description="Add one to get started." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Code</TH>
              <TH>Name</TH>
              <TH>Semesters</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {programs.map((program) => (
              <TR key={program.id}>
                <TD className="font-medium">{program.code}</TD>
                <TD>{program.name}</TD>
                <TD>{program.total_semesters}</TD>
                <TD className="text-right whitespace-nowrap">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(program)}>
                    Edit
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(program)}>
                    Delete
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <ProgramModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSaved={load} mode="create" />
      <ProgramModal
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={load}
        mode="edit"
        program={editing}
      />
    </div>
  )
}

function ProgramModal({ isOpen, onClose, onSaved, mode, program }) {
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [totalSemesters, setTotalSemesters] = useState('8')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setCode(program?.code ?? '')
      setName(program?.name ?? '')
      setTotalSemesters(program ? String(program.total_semesters) : '8')
      setError('')
    }
  }, [isOpen, program])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const data = { code, name, total_semesters: Number(totalSemesters) }
      if (mode === 'edit') {
        await updateProgram(program.id, data)
      } else {
        await createProgram(data)
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
    <Modal isOpen={isOpen} onClose={onClose} title={mode === 'edit' ? 'Edit Programme' : 'Add Programme'}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Code"
          placeholder="BSSE"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <Input
          label="Programme Name"
          placeholder="BS Software Engineering"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <Input
          label="Total Semesters"
          type="number"
          min="1"
          value={totalSemesters}
          onChange={(e) => setTotalSemesters(e.target.value)}
          required
        />
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
