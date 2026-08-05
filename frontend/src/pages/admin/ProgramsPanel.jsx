import { useEffect, useState } from 'react'
import { createProgram, listDepartments, listPrograms } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function ProgramsPanel() {
  const [programs, setPrograms] = useState(null)
  const [departments, setDepartments] = useState([])
  const [isModalOpen, setIsModalOpen] = useState(false)

  const load = () => listPrograms().then(setPrograms)

  useEffect(() => {
    load()
    listDepartments().then(setDepartments)
  }, [])

  const deptName = (deptId) => departments.find((d) => d.id === deptId)?.name ?? `#${deptId}`

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-500">Degree programmes offered by the institution.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} disabled={departments.length === 0}>
          + Add Programme
        </Button>
      </div>

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
              <TH>Department</TH>
              <TH>Semesters</TH>
            </TR>
          </THead>
          <TBody>
            {programs.map((program) => (
              <TR key={program.id}>
                <TD className="font-medium">{program.code}</TD>
                <TD>{program.name}</TD>
                <TD className="text-ink-500">{deptName(program.dept_id)}</TD>
                <TD>{program.total_semesters}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <CreateProgramModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={load}
        departments={departments}
      />
    </div>
  )
}

function CreateProgramModal({ isOpen, onClose, onCreated, departments }) {
  const [deptId, setDeptId] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [totalSemesters, setTotalSemesters] = useState('8')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setDeptId('')
    setCode('')
    setName('')
    setTotalSemesters('8')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createProgram({
        dept_id: Number(deptId || departments[0]?.id),
        code,
        name,
        total_semesters: Number(totalSemesters),
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
    <Modal isOpen={isOpen} onClose={onClose} title="Add Programme">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Select
          label="Department"
          value={deptId || departments[0]?.id || ''}
          onChange={(e) => setDeptId(e.target.value)}
        >
          {departments.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.name}
            </option>
          ))}
        </Select>
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
            Create
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
