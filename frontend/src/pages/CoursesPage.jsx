import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listPrograms } from '../api/admin'
import {
  createCourse,
  deleteCourse,
  listDepartmentCourses,
  listMyCourses,
  updateCourse,
} from '../api/courses'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal, { ModalFooter } from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody } from '../components/ui/Card'

export default function CoursesPage() {
  const { user } = useAuth()
  const isSubAdmin = user.role === 'sub_admin'

  const [courses, setCourses] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = () => (isSubAdmin ? listDepartmentCourses() : listMyCourses()).then(setCourses)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleDelete(e, course) {
    e.stopPropagation()
    if (!window.confirm(`Delete course "${course.code} — ${course.name}"? This cannot be undone.`))
      return
    setError('')
    try {
      await deleteCourse(course.id)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.')
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink-900">
              {isSubAdmin ? 'Department Courses' : 'My Courses'}
            </h1>
            <p className="text-sm text-ink-500 mt-0.5">
              {isSubAdmin ? 'Courses offered in your department' : 'Courses you own and teach'}
            </p>
          </div>
          <Button onClick={() => setIsModalOpen(true)} className="self-start sm:self-auto">
            + New Course
          </Button>
        </div>

        {error && (
          <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>
        )}

        {courses === null ? (
          <div className="flex justify-center py-24">
            <Spinner />
          </div>
        ) : courses.length === 0 ? (
          <Card>
            <EmptyState
              title="No courses yet"
              description="Create your first course to start defining CLOs and mapping them to PLOs."
              action={<Button onClick={() => setIsModalOpen(true)}>+ New Course</Button>}
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {courses.map((course) => (
              <Card
                key={course.id}
                className={isSubAdmin ? '' : 'cursor-pointer hover:border-brand-300 transition-colors'}
                onClick={() => !isSubAdmin && navigate(`/courses/${course.id}`)}
              >
                <CardBody>
                  <p className="text-xs font-medium text-brand-600">{course.code}</p>
                  <p className="text-sm font-semibold text-ink-900 mt-0.5">{course.name}</p>
                  <p className="text-xs text-ink-500 mt-2">
                    Semester {course.semester} · {course.credit_hours} credit hours
                  </p>
                  {isSubAdmin && (
                    <div className="flex justify-end gap-1 mt-3 -mb-1 -mr-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditing(course)
                        }}
                      >
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={(e) => handleDelete(e, course)}>
                        Delete
                      </Button>
                    </div>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </main>

      <CourseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaved={load}
        mode="create"
        existingCourses={courses ?? []}
      />
      <CourseModal
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={load}
        mode="edit"
        course={editing}
        existingCourses={courses ?? []}
      />
    </div>
  )
}

function CourseModal({ isOpen, onClose, onSaved, mode, course, existingCourses = [] }) {
  const [programs, setPrograms] = useState([])
  const [programId, setProgramId] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [creditHours, setCreditHours] = useState('3')
  const [semester, setSemester] = useState('1')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      listPrograms().then((data) => {
        setPrograms(data)
        if (mode === 'create' && data.length > 0) {
          setProgramId((current) => current || String(data[0].id))
        }
      })
    }
  }, [isOpen, mode])

  useEffect(() => {
    if (isOpen) {
      setProgramId(course ? String(course.program_id) : '')
      setCode(course?.code ?? '')
      setName(course?.name ?? '')
      setCreditHours(course ? String(course.credit_hours) : '3')
      setSemester(course ? String(course.semester) : '1')
      setError('')
    }
  }, [isOpen, course])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const duplicate = existingCourses.find(
      (c) =>
        c.id !== course?.id &&
        String(c.program_id) === programId &&
        c.code.trim().toLowerCase() === code.trim().toLowerCase() &&
        String(c.semester) === semester,
    )
    if (duplicate) {
      setError('A course with this code already exists for this programme and semester.')
      return
    }

    setIsSubmitting(true)
    try {
      const data = {
        program_id: Number(programId),
        code,
        name,
        credit_hours: Number(creditHours),
        semester: Number(semester),
      }
      if (mode === 'edit') {
        await updateCourse(course.id, data)
      } else {
        await createCourse(data)
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
    <Modal isOpen={isOpen} onClose={onClose} title={mode === 'edit' ? 'Edit Course' : 'New Course'}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Select label="Programme" value={programId} onChange={(e) => setProgramId(e.target.value)}>
          {programs.map((program) => (
            <option key={program.id} value={program.id}>
              {program.code} — {program.name}
            </option>
          ))}
        </Select>
        <Input
          label="Course Code"
          placeholder="SE-301"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <Input
          label="Course Name"
          placeholder="Software Design & Architecture"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Credit Hours"
            type="number"
            min="1"
            value={creditHours}
            onChange={(e) => setCreditHours(e.target.value)}
            required
          />
          <Input
            label="Semester"
            type="number"
            min="1"
            value={semester}
            onChange={(e) => setSemester(e.target.value)}
            required
          />
        </div>
        {error && <p className="text-sm text-danger-600 bg-danger-50 rounded-lg px-3 py-2">{error}</p>}
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting} disabled={programs.length === 0}>
            {mode === 'edit' ? 'Save' : 'Create'}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
