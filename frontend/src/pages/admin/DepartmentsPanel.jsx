import { useEffect, useState } from 'react'
import { createDepartment, deleteDepartment, listDepartments, updateDepartment } from '../../api/admin'
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
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')

  const load = () => listDepartments().then(setDepartments)

  useEffect(() => {
    load()
  }, [])

  async function handleDelete(dept) {
    if (!window.confirm(`Delete department "${dept.name}"? This cannot be undone.`)) return
    setError('')
    try {
      await deleteDepartment(dept.id)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Academic departments in the institution.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
          + Add Department
        </Button>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

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
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {departments.map((dept) => (
              <TR key={dept.id}>
                <TD className="font-medium">{dept.code}</TD>
                <TD>{dept.name}</TD>
                <TD className="text-right whitespace-nowrap">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(dept)}>
                    Edit
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(dept)}>
                    Delete
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <DepartmentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaved={load}
        mode="create"
      />
      <DepartmentModal
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={load}
        mode="edit"
        department={editing}
      />
    </div>
  )
}

function DepartmentModal({ isOpen, onClose, onSaved, mode, department }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setName(department?.name ?? '')
      setCode(department?.code ?? '')
      setError('')
    }
  }, [isOpen, department])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      if (mode === 'edit') {
        await updateDepartment(department.id, { name, code })
      } else {
        await createDepartment({ name, code })
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
    <Modal isOpen={isOpen} onClose={onClose} title={mode === 'edit' ? 'Edit Department' : 'Add Department'}>
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
            {mode === 'edit' ? 'Save' : 'Create'}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
