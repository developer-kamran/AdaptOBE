import { useEffect, useState } from 'react'
import { deactivateUser, listDepartments, listUsers, registerUser, updateUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

// Super Admin's view of Sub-Admins only. Faculty/Student management (with
// their own required fields and password reveal) lives in the sibling
// StudentsPanel/FacultyPanel components a sub_admin sees instead.
export default function UsersPanel() {
  const [users, setUsers] = useState(null)
  const [search, setSearch] = useState('')
  const [departments, setDepartments] = useState([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const load = () => listUsers().then(setUsers)

  useEffect(() => {
    load()
    listDepartments().then(setDepartments)
  }, [])

  const deptName = (deptId) => departments.find((d) => d.id === deptId)?.code ?? '—'

  async function handleDeactivate(userId) {
    await deactivateUser(userId)
    load()
  }

  async function handleReactivate(userId) {
    await updateUser(userId, { is_active: true })
    load()
  }

  const query = search.trim().toLowerCase()
  const filtered = (users ?? []).filter(
    (u) => !query || (u.employee_id ?? '').toLowerCase().includes(query),
  )

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Sub-admins, one per department.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
          + Add Sub-Admin
        </Button>
      </div>

      {users !== null && users.length > 0 && (
        <Input
          placeholder="Search by Employee ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs mb-4"
        />
      )}

      {users === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : users.length === 0 ? (
        <EmptyState title="No users yet" />
      ) : filtered.length === 0 ? (
        <EmptyState title="No sub-admins match that search" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Email</TH>
              <TH>Employee ID</TH>
              <TH>Department</TH>
              <TH>Status</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {filtered.map((u) => (
              <TR key={u.id}>
                <TD className="font-medium">{u.full_name}</TD>
                <TD className="text-ink-500">{u.email}</TD>
                <TD>{u.employee_id ?? '—'}</TD>
                <TD>{deptName(u.dept_id)}</TD>
                <TD>
                  <Badge tone={u.is_active ? 'success' : 'danger'}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </TD>
                <TD className="text-right whitespace-nowrap">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(u)}>
                    Edit
                  </Button>
                  {u.is_active ? (
                    <Button variant="ghost" size="sm" onClick={() => handleDeactivate(u.id)}>
                      Deactivate
                    </Button>
                  ) : (
                    <Button variant="ghost" size="sm" onClick={() => handleReactivate(u.id)}>
                      Reactivate
                    </Button>
                  )}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <RegisterUserModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={load}
        departments={departments}
      />
      <EditUserModal
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={load}
        departments={departments}
        target={editing}
      />
    </div>
  )
}

function RegisterUserModal({ isOpen, onClose, onCreated, departments }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const [deptId, setDeptId] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen && departments.length > 0) {
      setDeptId((current) => current || String(departments[0].id))
    }
  }, [isOpen, departments])

  function reset() {
    setEmail('')
    setPassword('')
    setFullName('')
    setEmployeeId('')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await registerUser({
        email,
        password,
        full_name: fullName,
        role: 'sub_admin',
        employee_id: employeeId,
        dept_id: Number(deptId),
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
    <Modal isOpen={isOpen} onClose={onClose} title="Add Sub-Admin">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Full Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        <Input
          label="Employee ID"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          required
        />
        <Select label="Department" value={deptId} onChange={(e) => setDeptId(e.target.value)}>
          {departments.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.code} — {dept.name}
            </option>
          ))}
        </Select>

        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Add Sub-Admin
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}

function EditUserModal({ isOpen, onClose, onSaved, departments, target }) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const [deptId, setDeptId] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen && target) {
      setFullName(target.full_name)
      setEmail(target.email)
      setEmployeeId(target.employee_id ?? '')
      setDeptId(target.dept_id != null ? String(target.dept_id) : '')
      setError('')
    }
  }, [isOpen, target])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await updateUser(target.id, {
        full_name: fullName,
        email,
        employee_id: employeeId,
        dept_id: Number(deptId),
      })
      onClose()
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!target) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Edit ${target.full_name}`}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          label="Employee ID"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          required
        />
        <Select label="Department" value={deptId} onChange={(e) => setDeptId(e.target.value)}>
          {departments.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.code} — {dept.name}
            </option>
          ))}
        </Select>

        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Save
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
