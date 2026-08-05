import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listPrograms } from '../api/admin'
import { createCourse, listMyCourses } from '../api/courses'
import { ApiError } from '../api/client'
import Navbar from '../components/Navbar'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal, { ModalFooter } from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody } from '../components/ui/Card'

export default function CoursesPage() {
  const [courses, setCourses] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const navigate = useNavigate()

  const load = () => listMyCourses().then(setCourses)

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink-900">My Courses</h1>
            <p className="text-sm text-ink-500 mt-0.5">Courses you own and teach</p>
          </div>
          <Button onClick={() => setIsModalOpen(true)}>+ New Course</Button>
        </div>

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
                className="cursor-pointer hover:border-brand-300 transition-colors"
                onClick={() => navigate(`/courses/${course.id}`)}
              >
                <CardBody>
                  <p className="text-xs font-medium text-brand-600">{course.code}</p>
                  <p className="text-sm font-semibold text-ink-900 mt-0.5">{course.name}</p>
                  <p className="text-xs text-ink-500 mt-2">
                    Semester {course.semester} · {course.credit_hours} credit hours
                  </p>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </main>

      <CreateCourseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={load}
      />
    </div>
  )
}

function CreateCourseModal({ isOpen, onClose, onCreated }) {
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
        if (data.length > 0) setProgramId((current) => current || String(data[0].id))
      })
    }
  }, [isOpen])

  function reset() {
    setCode('')
    setName('')
    setCreditHours('3')
    setSemester('1')
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await createCourse({
        program_id: Number(programId),
        code,
        name,
        credit_hours: Number(creditHours),
        semester: Number(semester),
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
    <Modal isOpen={isOpen} onClose={onClose} title="New Course">
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
        <div className="grid grid-cols-2 gap-3">
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
            Create
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
