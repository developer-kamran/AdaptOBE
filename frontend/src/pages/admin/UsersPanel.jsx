import { useEffect, useState } from 'react'
import { deactivateUser, listUsers, registerUser } from '../../api/admin'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import Badge from '../../components/ui/Badge'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

const ROLE_TONE = { admin: 'brand', faculty: 'success', student: 'neutral' }

export default function UsersPanel() {
  const [users, setUsers] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const load = () => listUsers().then(setUsers)

  useEffect(() => {
    load()
  }, [])

  async function handleDeactivate(userId) {
    await deactivateUser(userId)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-500">Everyone with an AdaptOBE account.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)}>
          + Register User
        </Button>
      </div>

      {users === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : users.length === 0 ? (
        <EmptyState title="No users yet" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Email</TH>
              <TH>Role</TH>
              <TH>Status</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {users.map((user) => (
              <TR key={user.id}>
                <TD className="font-medium">{user.full_name}</TD>
                <TD className="text-ink-500">{user.email}</TD>
                <TD>
                  <Badge tone={ROLE_TONE[user.role]} className="capitalize">
                    {user.role}
                  </Badge>
                </TD>
                <TD>
                  <Badge tone={user.is_active ? 'success' : 'danger'}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </TD>
                <TD>
                  {user.is_active && (
                    <Button variant="ghost" size="sm" onClick={() => handleDeactivate(user.id)}>
                      Deactivate
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
      />
    </div>
  )
}

function RegisterUserModal({ isOpen, onClose, onCreated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState('student')
  const [enrollmentNo, setEnrollmentNo] = useState('')
  const [seatNo, setSeatNo] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function reset() {
    setEmail('')
    setPassword('')
    setFullName('')
    setRole('student')
    setEnrollmentNo('')
    setSeatNo('')
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
        role,
        enrollment_no: role === 'student' && enrollmentNo ? enrollmentNo : undefined,
        seat_no: role === 'student' && seatNo ? seatNo : undefined,
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
    <Modal isOpen={isOpen} onClose={onClose} title="Register User">
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
        <Select label="Role" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="admin">Admin</option>
        </Select>
        {role === 'student' && (
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Enrollment No (optional)"
              value={enrollmentNo}
              onChange={(e) => setEnrollmentNo(e.target.value)}
            />
            <Input
              label="Seat No (optional)"
              value={seatNo}
              onChange={(e) => setSeatNo(e.target.value)}
            />
          </div>
        )}
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
