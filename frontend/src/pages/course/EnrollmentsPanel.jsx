import { useEffect, useState } from 'react'
import { enrollStudents, listEnrollments, listStudents, unenrollStudent } from '../../api/enrollments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'

export default function EnrollmentsPanel({ course }) {
  const [enrollments, setEnrollments] = useState(null)
  const [studentLookup, setStudentLookup] = useState(new Map())
  const [isModalOpen, setIsModalOpen] = useState(false)

  const load = () => listEnrollments(course.id).then(setEnrollments)

  useEffect(() => {
    load()
    listStudents().then((all) => setStudentLookup(new Map(all.map((s) => [s.id, s]))))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course.id])

  async function handleUnenroll(studentId) {
    await unenrollStudent(course.id, studentId)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-ink-500">Students enrolled in {course.code}.</p>
        <Button size="sm" onClick={() => setIsModalOpen(true)}>
          + Enroll Students
        </Button>
      </div>

      {enrollments === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : enrollments.length === 0 ? (
        <EmptyState title="No students enrolled yet" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Email</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {enrollments.map((enrollment) => {
              const student = studentLookup.get(enrollment.student_id)
              return (
                <TR key={enrollment.id}>
                  <TD className="font-medium">{student?.full_name ?? `#${enrollment.student_id}`}</TD>
                  <TD className="text-ink-500">{student?.email}</TD>
                  <TD>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleUnenroll(enrollment.student_id)}
                    >
                      Remove
                    </Button>
                  </TD>
                </TR>
              )
            })}
          </TBody>
        </Table>
      )}

      <EnrollModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onEnrolled={load}
        course={course}
        alreadyEnrolled={new Set((enrollments ?? []).map((e) => e.student_id))}
      />
    </div>
  )
}

function EnrollModal({ isOpen, onClose, onEnrolled, course, alreadyEnrolled }) {
  const [students, setStudents] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      listStudents().then(setStudents)
      setSelected(new Set())
      setError('')
    }
  }, [isOpen])

  function toggle(studentId) {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(studentId)) next.delete(studentId)
      else next.add(studentId)
      return next
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (selected.size === 0) return
    setError('')
    setIsSubmitting(true)
    try {
      await enrollStudents(course.id, Array.from(selected))
      onClose()
      onEnrolled()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const available = students.filter((s) => !alreadyEnrolled.has(s.id))

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Enroll Students">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {available.length === 0 ? (
          <p className="text-sm text-ink-500">All active students are already enrolled.</p>
        ) : (
          <div className="max-h-72 overflow-y-auto border border-border rounded-lg divide-y divide-border">
            {available.map((student) => (
              <label
                key={student.id}
                className="flex items-center gap-3 px-3 py-2.5 text-sm cursor-pointer hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={selected.has(student.id)}
                  onChange={() => toggle(student.id)}
                  className="h-4 w-4 rounded border-border-strong text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <p className="font-medium text-ink-900">{student.full_name}</p>
                  <p className="text-xs text-ink-500">{student.email}</p>
                </div>
              </label>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting} disabled={selected.size === 0}>
            Enroll {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
