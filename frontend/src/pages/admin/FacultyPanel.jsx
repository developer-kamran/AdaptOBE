import { useEffect, useState } from 'react'
import { deactivateUser, getUserPassword, listUsers, registerUser, updateUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import PasswordRevealField from '../../components/ui/PasswordRevealField'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function FacultyPanel() {
  const [faculty, setFaculty] = useState(null)
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const load = () => listUsers().then((users) => setFaculty(users.filter((u) => u.role === 'faculty')))

  useEffect(() => {
    load()
  }, [])

  async function handleDeactivate(userId) {
    await deactivateUser(userId)
    load()
  }

  async function handleReactivate(userId) {
    await updateUser(userId, { is_active: true })
    load()
  }

  const query = search.trim().toLowerCase()
  const filtered = (faculty ?? []).filter(
    (u) => !query || (u.employee_id ?? '').toLowerCase().includes(query),
  )

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Faculty in your department.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
          + Add Faculty
        </Button>
      </div>

      {faculty !== null && faculty.length > 0 && (
        <Input
          placeholder="Search by Faculty ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs mb-4"
        />
      )}

      {faculty === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : faculty.length === 0 ? (
        <EmptyState title="No faculty yet" />
      ) : filtered.length === 0 ? (
        <EmptyState title="No faculty match that search" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Email</TH>
              <TH>Faculty ID</TH>
              <TH>Status</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {filtered.map((u) => (
              <TR key={u.id}>
                <TD className="font-medium">{u.full_name}</TD>
                <TD className="text-ink-500">{u.email}</TD>
                <TD className="text-ink-500">{u.employee_id ?? '—'}</TD>
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

      <RegisterFacultyModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onCreated={load} />
      <EditFacultyModal isOpen={editing !== null} onClose={() => setEditing(null)} onSaved={load} target={editing} />
    </div>
  )
}

function RegisterFacultyModal({ isOpen, onClose, onCreated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [facultyId, setFacultyId] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setEmail('')
    setPassword('')
    setFullName('')
    setFacultyId('')
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
        role: 'faculty',
        employee_id: facultyId,
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
    <Modal isOpen={isOpen} onClose={onClose} title="Add Faculty">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <Input
          label="Faculty ID"
          value={facultyId}
          onChange={(e) => setFacultyId(e.target.value)}
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
        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Register
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}

function EditFacultyModal({ isOpen, onClose, onSaved, target }) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [facultyId, setFacultyId] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [password, setPassword] = useState(undefined)
  const [isPasswordLoading, setIsPasswordLoading] = useState(false)

  useEffect(() => {
    if (isOpen && target) {
      setFullName(target.full_name)
      setEmail(target.email)
      setFacultyId(target.employee_id ?? '')
      setError('')
      setPassword(undefined)
      setIsPasswordLoading(true)
      getUserPassword(target.id)
        .then((res) => setPassword(res.password))
        .finally(() => setIsPasswordLoading(false))
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
        employee_id: facultyId,
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
          label="Faculty ID"
          value={facultyId}
          onChange={(e) => setFacultyId(e.target.value)}
          required
        />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <PasswordRevealField password={password} isLoading={isPasswordLoading} />
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
