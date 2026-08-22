import { useEffect, useState } from 'react'
import { enrollStudents, listStudents } from '../../api/enrollments'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal, { ModalFooter } from '../../components/ui/Modal'

// Enrolls a "backlog" student -- someone repeating this course from an
// earlier cohort, possibly a different programme, so the normal picker
// (scoped to the course's own programme + current-batch year) deliberately
// doesn't apply here. The backend (backlog=true) already restricts the pool
// to department students whose seat number encodes an earlier enrollment
// year than this course's current batch -- this modal just searches that
// pool by Seat No or Enrollment No as the faculty types.
export default function BacklogEnrollModal({ isOpen, onClose, onEnrolled, course, alreadyEnrolled }) {
  const [candidates, setCandidates] = useState([])
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      listStudents(course.id, { backlog: true }).then(setCandidates)
      setQuery('')
      setSelected(new Set())
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
      const ids = Array.from(selected)
      await enrollStudents(course.id, ids)
      onClose()
      onEnrolled(ids)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const trimmed = query.trim().toLowerCase()
  const matches = trimmed
    ? candidates
        .filter(
          (s) =>
            !alreadyEnrolled.has(s.id) &&
            ((s.seat_no ?? '').toLowerCase().includes(trimmed) ||
              (s.enrollment_no ?? '').toLowerCase().includes(trimmed)),
        )
        .sort((a, b) => a.full_name.localeCompare(b.full_name, undefined, { sensitivity: 'base' }))
    : []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Backlog Student"
      description="Search students from an earlier batch (any programme in the department) by Seat No or Enrollment No."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          placeholder="Type a Seat No or Enrollment No…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />

        {!trimmed ? (
          <p className="text-sm text-ink-500 py-4 text-center">
            Start typing to search students from an earlier batch.
          </p>
        ) : matches.length === 0 ? (
          <p className="text-sm text-ink-500 py-4 text-center">No matching students found.</p>
        ) : (
          <div className="max-h-64 overflow-y-auto border border-border rounded-lg divide-y divide-border">
            {matches.map((student) => (
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
                  <p className="text-xs text-ink-500">
                    {student.seat_no ?? '—'} · {student.enrollment_no ?? '—'}
                  </p>
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
            Add {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
