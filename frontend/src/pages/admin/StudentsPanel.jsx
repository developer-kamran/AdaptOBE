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
import BulkStudentImportModal from './BulkStudentImportModal'

export default function StudentsPanel() {
  const [students, setStudents] = useState(null)
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const load = () => listUsers().then((users) => setStudents(users.filter((u) => u.role === 'student')))

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
  const filtered = (students ?? []).filter(
    (u) =>
      !query ||
      (u.seat_no ?? '').toLowerCase().includes(query) ||
      (u.enrollment_no ?? '').toLowerCase().includes(query),
  )

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Students in your department.</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => setIsImportOpen(true)}>
            Add Students via File
          </Button>
          <Button size="sm" onClick={() => setIsModalOpen(true)}>
            + Add Student
          </Button>
        </div>
      </div>

      {students !== null && students.length > 0 && (
        <Input
          placeholder="Search by Seat No or Enrollment No…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs mb-4"
        />
      )}

      {students === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : students.length === 0 ? (
        <EmptyState title="No students yet" />
      ) : filtered.length === 0 ? (
        <EmptyState title="No students match that search" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Father's Name</TH>
              <TH>Email</TH>
              <TH>Enrollment / Seat</TH>
              <TH>Status</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {filtered.map((u) => (
              <TR key={u.id}>
                <TD className="font-medium">{u.full_name}</TD>
                <TD className="text-ink-500">{u.father_name ?? '—'}</TD>
                <TD className="text-ink-500">{u.email}</TD>
                <TD className="text-ink-500">{u.enrollment_no ?? '—'} / {u.seat_no ?? '—'}</TD>
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

      <RegisterStudentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onCreated={load} />
      <BulkStudentImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onImported={load}
      />
      <EditStudentModal isOpen={editing !== null} onClose={() => setEditing(null)} onSaved={load} target={editing} />
    </div>
  )
}

function RegisterStudentModal({ isOpen, onClose, onCreated }) {
  const [step, setStep] = useState('form') // form | result
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [fatherName, setFatherName] = useState('')
  const [enrollmentNo, setEnrollmentNo] = useState('')
  const [seatNo, setSeatNo] = useState('')
  const [created, setCreated] = useState(null)
  const [password, setPassword] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setStep('form')
    setEmail('')
    setFullName('')
    setFatherName('')
    setEnrollmentNo('')
    setSeatNo('')
    setCreated(null)
    setPassword(null)
    setError('')
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      // No password field -- the backend generates one (same criteria as
      // bulk import) since no human should have to pick one here.
      const student = await registerUser({
        email,
        full_name: fullName,
        role: 'student',
        father_name: fatherName,
        enrollment_no: enrollmentNo,
        seat_no: seatNo,
      })
      const { password: generatedPassword } = await getUserPassword(student.id)
      setCreated(student)
      setPassword(generatedPassword)
      setStep('result')
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={step === 'result' ? 'Student Added' : 'Add Student'}
      description={
        step === 'result'
          ? 'Share this password with the student — it can also be viewed later from Edit.'
          : undefined
      }
    >
      {step === 'form' && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          <Input
            label="Father's Name"
            value={fatherName}
            onChange={(e) => setFatherName(e.target.value)}
            required
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Enrollment No"
              value={enrollmentNo}
              onChange={(e) => setEnrollmentNo(e.target.value)}
              required
            />
            <Input label="Seat No" value={seatNo} onChange={(e) => setSeatNo(e.target.value)} required />
          </div>
          <p className="text-xs text-ink-500 -mt-2">
            A password is generated automatically and shown once you register.
          </p>
          {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
          <ModalFooter>
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Register
            </Button>
          </ModalFooter>
        </form>
      )}

      {step === 'result' && created && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs font-medium text-ink-500">Full Name</p>
              <p className="text-ink-900">{created.full_name}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-ink-500">Father's Name</p>
              <p className="text-ink-900">{fatherName}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-ink-500">Email</p>
              <p className="text-ink-900">{created.email}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-ink-500">Enrollment No</p>
              <p className="text-ink-900">{created.enrollment_no}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-ink-500">Seat No</p>
              <p className="text-ink-900">{created.seat_no}</p>
            </div>
          </div>
          <PasswordRevealField password={password} isLoading={false} />
          <ModalFooter>
            <Button type="button" onClick={handleClose}>
              Done
            </Button>
          </ModalFooter>
        </div>
      )}
    </Modal>
  )
}

function EditStudentModal({ isOpen, onClose, onSaved, target }) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [fatherName, setFatherName] = useState('')
  const [enrollmentNo, setEnrollmentNo] = useState('')
  const [seatNo, setSeatNo] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [password, setPassword] = useState(undefined)
  const [isPasswordLoading, setIsPasswordLoading] = useState(false)

  useEffect(() => {
    if (isOpen && target) {
      setFullName(target.full_name)
      setEmail(target.email)
      setFatherName(target.father_name ?? '')
      setEnrollmentNo(target.enrollment_no ?? '')
      setSeatNo(target.seat_no ?? '')
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
        father_name: fatherName,
        enrollment_no: enrollmentNo,
        seat_no: seatNo,
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
          label="Father's Name"
          value={fatherName}
          onChange={(e) => setFatherName(e.target.value)}
          required
        />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Enrollment No"
            value={enrollmentNo}
            onChange={(e) => setEnrollmentNo(e.target.value)}
            required
          />
          <Input label="Seat No" value={seatNo} onChange={(e) => setSeatNo(e.target.value)} required />
        </div>
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
