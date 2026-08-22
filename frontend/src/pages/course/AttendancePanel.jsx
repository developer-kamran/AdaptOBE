import { useEffect, useMemo, useState } from 'react'
import { listEnrollments, listStudents } from '../../api/enrollments'
import { listAttendance, setAttendance } from '../../api/attendance'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import { Table, THead, TH, TBody, TR, TD } from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import InfoTooltip from '../../components/ui/InfoTooltip'
import Badge from '../../components/ui/Badge'
import { isBacklogStudent } from '../../utils/seatNo'
import AttendanceImportModal from './AttendanceImportModal'

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
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [search, setSearch] = useState('')
  // One threshold filter active at a time -- `filterMode` picks which
  // comparison applies, `filterValue` is the % it's compared against.
  const [filterMode, setFilterMode] = useState('none') // none | below | above
  const [filterValue, setFilterValue] = useState('')

  async function load() {
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
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Seat-No order, not whatever order the enrollments API happens to return
  // (roughly enrollment-id order, i.e. effectively random from a faculty's
  // point of view). `numeric: true` sorts the trailing digits in a seat
  // number ("...081" vs "...007") numerically rather than lexicographically.
  // Backlog students (seat number encodes an earlier batch year than this
  // course's semester currently expects) are pulled out and appended at the
  // bottom instead, highlighted -- they're repeating this course from an
  // earlier cohort, so mixing them into the regular seat-no sequence would
  // be misleading.
  const seatSortedEnrollments = useMemo(() => {
    const sorted = [...(enrollments ?? [])].sort((a, b) => {
      const seatA = studentLookup.get(a.student_id)?.seat_no ?? ''
      const seatB = studentLookup.get(b.student_id)?.seat_no ?? ''
      return seatA.localeCompare(seatB, undefined, { numeric: true, sensitivity: 'base' })
    })
    const isBacklog = (e) => isBacklogStudent(studentLookup.get(e.student_id)?.seat_no, course.semester)
    const regular = sorted.filter((e) => !isBacklog(e))
    const backlog = sorted.filter(isBacklog)
    return [...regular, ...backlog]
  }, [enrollments, studentLookup, course.semester])

  const query = search.trim().toLowerCase()
  const threshold = filterMode !== 'none' && filterValue.trim() !== '' ? Number(filterValue) : null
  const visibleEnrollments = seatSortedEnrollments.filter((enrollment) => {
    const student = studentLookup.get(enrollment.student_id)
    if (query) {
      const name = (student?.full_name ?? '').toLowerCase()
      const seatNo = (student?.seat_no ?? '').toLowerCase()
      if (!name.includes(query) && !seatNo.includes(query)) return false
    }
    if (threshold !== null && !Number.isNaN(threshold)) {
      const raw = values.get(enrollment.student_id)
      if (raw === undefined || raw === '') return false // no recorded attendance yet
      const value = Number(raw)
      if (Number.isNaN(value)) return false
      if (filterMode === 'below' && value >= threshold) return false
      if (filterMode === 'above' && value <= threshold) return false
    }
    return true
  })

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
          <Button variant="secondary" size="sm" onClick={() => setIsImportOpen(true)}>
            Upload Attendance
          </Button>
          <Button size="sm" onClick={handleSave} isLoading={isSaving}>
            Save Attendance
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2 mb-4">{error}</p>
      )}

      {enrollments !== null && enrollments.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-3 mb-4">
          <Input
            placeholder="Search by Name or Seat No…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs"
          />
          <div className="flex items-center gap-2">
            <label htmlFor="attendance-filter-mode" className="text-sm text-ink-500 whitespace-nowrap">
              Attendance
            </label>
            <Select
              id="attendance-filter-mode"
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value)}
              className="w-28"
            >
              <option value="none">No filter</option>
              <option value="below">Below</option>
              <option value="above">Above</option>
            </Select>
            {filterMode !== 'none' && (
              <>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  placeholder={filterMode === 'below' ? 'e.g. 50' : 'e.g. 90'}
                  value={filterValue}
                  onChange={(e) => setFilterValue(e.target.value)}
                  className="w-24"
                />
                <span className="text-sm text-ink-500">%</span>
              </>
            )}
            {(filterMode !== 'none' || filterValue !== '') && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFilterMode('none')
                  setFilterValue('')
                }}
              >
                Clear
              </Button>
            )}
          </div>
          <p className="text-sm text-ink-500 sm:ml-auto whitespace-nowrap">
            Showing {visibleEnrollments.length} student{visibleEnrollments.length === 1 ? '' : 's'}
          </p>
        </div>
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
      ) : visibleEnrollments.length === 0 ? (
        <EmptyState title="No students match these filters" />
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

      <AttendanceImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onImported={load}
        course={course}
      />
    </div>
  )
}
