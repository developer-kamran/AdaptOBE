import { useEffect, useState } from 'react'
import { createDepartment, listDepartments } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function DepartmentsPanel() {
  const [departments, setDepartments] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const load = () => listDepartments().then(setDepartments)

  useEffect(() => {
    load()
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-500">Academic departments in the institution.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)}>
          + Add Department
        </Button>
      </div>

      {departments === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : departments.length === 0 ? (
        <EmptyState title="No departments yet" description="Add one to get started." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Code</TH>
              <TH>Name</TH>
            </TR>
          </THead>
          <TBody>
            {departments.map((dept) => (
              <TR key={dept.id}>
                <TD className="font-medium">{dept.code}</TD>
                <TD>{dept.name}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <CreateDepartmentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={load}
      />
    </div>
  )
}

function CreateDepartmentModal({ isOpen, onClose, onCreated }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setName('')
    setCode('')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createDepartment({ name, code })
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
    <Modal isOpen={isOpen} onClose={onClose} title="Add Department">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Department Name"
          placeholder="Department of Computer Science"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <Input
          label="Code"
          placeholder="UBIT"
          value={code}
          onChange={(e) => setCode(e.target.value)}
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
