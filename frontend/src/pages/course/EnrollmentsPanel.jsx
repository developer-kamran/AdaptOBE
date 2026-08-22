import { useEffect, useMemo, useState } from 'react'
import { enrollStudents, listEnrollments, listStudents, unenrollStudent } from '../../api/enrollments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import Badge from '../../components/ui/Badge'
import { isBacklogStudent } from '../../utils/seatNo'
import EnrollImportModal from './EnrollImportModal'
import BacklogEnrollModal from './BacklogEnrollModal'

export default function EnrollmentsPanel({ course }) {
  const [enrollments, setEnrollments] = useState(null)
  const [studentLookup, setStudentLookup] = useState(new Map())
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [isBacklogOpen, setIsBacklogOpen] = useState(false)

  const load = () => listEnrollments(course.id).then(setEnrollments)
  // Not scoped to course.program_id -- a backlog student can be enrolled
  // from anywhere in the department, so the lookup used to render the
  // already-enrolled table must be able to resolve any of them, not just
  // this course's own programme.
  const loadStudentLookup = () =>
    listStudents().then((all) => setStudentLookup(new Map(all.map((s) => [s.id, s]))))

  useEffect(() => {
    load()
    loadStudentLookup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course.id])

  async function handleUnenroll(studentId) {
    const name = studentLookup.get(studentId)?.full_name ?? `student #${studentId}`
    if (!window.confirm(`Remove ${name} from ${course.code}?`)) return
    await unenrollStudent(course.id, studentId)
    load()
  }

  function handleBacklogEnrolled() {
    setSearch('') // clear any active filter so the newly-added row is visible
    load()
    loadStudentLookup()
  }

  // Alphabetical by student name, not whatever order the enrollments API
  // happens to return (roughly enrollment-id order) -- except backlog
  // students (seat number encodes an earlier batch year than this course's
  // semester currently expects, same computed check as AttendancePanel's)
  // stay pinned at the bottom instead of sorting into alphabetical
  // position, since they're repeating this course from an earlier cohort.
  // Computed, not "just added this session", so it's consistent on every
  // reload rather than only right after using "+ Add Backlog Student".
  const nameSortedEnrollments = useMemo(() => {
    const sorted = [...(enrollments ?? [])].sort((a, b) => {
      const nameA = studentLookup.get(a.student_id)?.full_name ?? ''
      const nameB = studentLookup.get(b.student_id)?.full_name ?? ''
      return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' })
    })
    const isBacklog = (e) => isBacklogStudent(studentLookup.get(e.student_id)?.seat_no, course.semester)
    const regular = sorted.filter((e) => !isBacklog(e))
    const backlog = sorted.filter(isBacklog)
    return [...regular, ...backlog]
  }, [enrollments, studentLookup, course.semester])

  const seatQuery = search.trim().toLowerCase()
  const visibleEnrollments = nameSortedEnrollments.filter((enrollment) => {
    if (!seatQuery) return true
    const seatNo = studentLookup.get(enrollment.student_id)?.seat_no ?? ''
    return seatNo.toLowerCase().includes(seatQuery)
  })

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500">Students enrolled in {course.code}.</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => setIsImportOpen(true)}>
            Add Students via File
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setIsBacklogOpen(true)}>
            + Add Backlog Student
          </Button>
          <Button size="sm" onClick={() => setIsModalOpen(true)}>
            + Enroll Students
          </Button>
        </div>
      </div>

      {enrollments !== null && enrollments.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
          <Input
            placeholder="Search by Seat No…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs"
          />
          <p className="text-sm text-ink-500 sm:ml-auto whitespace-nowrap">
            {enrollments.length} student{enrollments.length === 1 ? '' : 's'} enrolled
          </p>
        </div>
      )}

      {enrollments === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : enrollments.length === 0 ? (
        <EmptyState title="No students enrolled yet" />
      ) : visibleEnrollments.length === 0 ? (
        <EmptyState title="No enrolled students match that search" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Father's Name</TH>
              <TH>Seat No.</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {visibleEnrollments.map((enrollment) => {
              const student = studentLookup.get(enrollment.student_id)
              const backlog = isBacklogStudent(student?.seat_no, course.semester)
              return (
                <TR
                  key={enrollment.id}
                  className={backlog ? 'bg-warning-50 ring-1 ring-inset ring-amber-200' : ''}
                >
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-1.5">
                      {student?.full_name ?? `#${enrollment.student_id}`}
                      {backlog && <Badge tone="warning">Backlog</Badge>}
                    </span>
                  </TD>
                  <TD className="text-ink-500">{student?.father_name ?? '—'}</TD>
                  <TD className="text-ink-500">{student?.seat_no ?? '—'}</TD>
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

      <BacklogEnrollModal
        isOpen={isBacklogOpen}
        onClose={() => setIsBacklogOpen(false)}
        onEnrolled={handleBacklogEnrolled}
        course={course}
        alreadyEnrolled={new Set((enrollments ?? []).map((e) => e.student_id))}
      />

      <EnrollImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onEnrolled={() => {
          load()
          loadStudentLookup()
        }}
        course={course}
      />
    </div>
  )
}

function EnrollModal({ isOpen, onClose, onEnrolled, course, alreadyEnrolled }) {
  const [students, setStudents] = useState([])
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      // Current-batch students for this course's programme + semester only.
      listStudents(course.id).then(setStudents)
      setSelected(new Set())
      setSearch('')
      setError('')
    }
  }, [isOpen, course.id])

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

  const available = students
    .filter((s) => !alreadyEnrolled.has(s.id))
    .sort((a, b) => a.full_name.localeCompare(b.full_name, undefined, { sensitivity: 'base' }))
  const seatQuery = search.trim().toLowerCase()
  const visible = available.filter(
    (s) => !seatQuery || (s.seat_no ?? '').toLowerCase().includes(seatQuery),
  )

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Enroll Students">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {available.length === 0 ? (
          <p className="text-sm text-ink-500">All active students are already enrolled.</p>
        ) : (
          <>
            <Input
              placeholder="Search by Seat No…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {visible.length === 0 ? (
              <p className="text-sm text-ink-500">No students match that search.</p>
            ) : (
              <div className="max-h-72 overflow-y-auto border border-border rounded-lg divide-y divide-border">
                {visible.map((student) => (
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
          </>
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
