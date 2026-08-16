import { useEffect, useState } from 'react'
import { listEnrollments, listStudents } from '../../api/enrollments'
import { listAttendance, setAttendance } from '../../api/attendance'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import InfoTooltip from '../../components/ui/InfoTooltip'

// Faculty enter one attendance percentage per enrolled student. It is the one
// XGBoost risk feature with no other source (scores, CLO attainment, etc. are
// all derived automatically), so it lives here rather than being computed.
export default function AttendancePanel({ course }) {
  const [enrollments, setEnrollments] = useState(null)
  const [studentLookup, setStudentLookup] = useState(new Map())
  const [values, setValues] = useState(new Map()) // student_id -> string
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      const [enrolled, allStudents, attendance] = await Promise.all([
        listEnrollments(course.id),
        listStudents(),
        listAttendance(course.id),
      ])
      setStudentLookup(new Map(allStudents.map((s) => [s.id, s])))
      const seeded = new Map(
        attendance.map((row) => [row.student_id, String(row.attendance_percentage)]),
      )
      setValues(seeded)
      setEnrollments(enrolled)
    })()
  }, [course.id])

  function handleChange(studentId, raw) {
    setSavedAt(false)
    setValues((current) => {
      const next = new Map(current)
      next.set(studentId, raw)
      return next
    })
  }

  async function handleSave() {
    setError('')
    const entries = []
    for (const enrollment of enrollments) {
      const raw = values.get(enrollment.student_id)
      if (raw === undefined || raw === '') continue
      const percentage = Number(raw)
      if (Number.isNaN(percentage) || percentage < 0 || percentage > 100) {
        setError('Attendance must be a number between 0 and 100.')
        return
      }
      entries.push({ student_id: enrollment.student_id, attendance_percentage: percentage })
    }
    if (entries.length === 0) {
      setError('Enter attendance for at least one student before saving.')
      return
    }

    setIsSaving(true)
    try {
      await setAttendance(course.id, entries)
      setSavedAt(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <p className="text-sm text-ink-500 inline-flex items-center gap-1.5">
          Attendance % for {course.code}
          <InfoTooltip>
            Attendance feeds the ML risk model as one of its five features. Enter
            each student's overall attendance percentage for the course, then run
            a risk prediction from the Attainment Dashboard.
          </InfoTooltip>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {savedAt && <span className="text-sm text-success-700">Saved ✓</span>}
          <Button size="sm" onClick={handleSave} isLoading={isSaving}>
            Save Attendance
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {enrollments === null ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : enrollments.length === 0 ? (
        <EmptyState
          title="No students enrolled yet"
          description="Enroll students first, then record their attendance here."
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Seat No.</TH>
              <TH className="w-40">Attendance %</TH>
            </TR>
          </THead>
          <TBody>
            {enrollments.map((enrollment) => {
              const student = studentLookup.get(enrollment.student_id)
              return (
                <TR key={enrollment.id}>
                  <TD className="font-medium">
                    {student?.full_name ?? `#${enrollment.student_id}`}
                  </TD>
                  <TD className="text-ink-500">{student?.seat_no ?? '—'}</TD>
                  <TD>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      placeholder="—"
                      value={values.get(enrollment.student_id) ?? ''}
                      onChange={(e) => handleChange(enrollment.student_id, e.target.value)}
                      className="w-28"
                    />
                  </TD>
                </TR>
              )
            })}
          </TBody>
        </Table>
      )}
    </div>
  )
}
