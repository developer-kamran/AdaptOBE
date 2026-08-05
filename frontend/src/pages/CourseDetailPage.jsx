import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getCourse } from '../api/courses'
import Navbar from '../components/Navbar'
import Tabs from '../components/ui/Tabs'
import Spinner from '../components/ui/Spinner'
import { Card, CardBody } from '../components/ui/Card'
import CLOsPanel from './course/CLOsPanel'
import EnrollmentsPanel from './course/EnrollmentsPanel'
import AssessmentsPanel from './course/AssessmentsPanel'

const TABS = [
  { value: 'clos', label: 'CLOs & Mappings' },
  { value: 'enrollments', label: 'Enrollments' },
  { value: 'assessments', label: 'Assessments' },
]

export default function CourseDetailPage() {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const [course, setCourse] = useState(null)
  const [active, setActive] = useState('clos')

  useEffect(() => {
    getCourse(Number(courseId)).then(setCourse)
  }, [courseId])

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 flex flex-col gap-5">
        <div>
          <Link to="/courses" className="text-xs text-brand-600 hover:text-brand-700 font-medium">
            ← My Courses
          </Link>
          {course ? (
            <div className="flex items-center justify-between mt-1">
              <div>
                <h1 className="text-xl font-semibold text-ink-900">
                  {course.code} — {course.name}
                </h1>
                <p className="text-sm text-ink-500 mt-0.5">
                  Semester {course.semester} · {course.credit_hours} credit hours
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                View Attainment Dashboard →
              </button>
            </div>
          ) : (
            <div className="h-10" />
          )}
        </div>

        {course === null ? (
          <div className="flex justify-center py-24">
            <Spinner />
          </div>
        ) : (
          <>
            <Tabs tabs={TABS} active={active} onChange={setActive} />
            <Card>
              <CardBody>
                {active === 'clos' && <CLOsPanel course={course} />}
                {active === 'enrollments' && <EnrollmentsPanel course={course} />}
                {active === 'assessments' && <AssessmentsPanel course={course} />}
              </CardBody>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}
