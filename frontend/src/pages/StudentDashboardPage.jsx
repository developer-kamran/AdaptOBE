import { useEffect, useState } from 'react'
import { getCourseScores, getProgress } from '../api/student'
import Navbar from '../components/Navbar'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import StatTile from '../components/ui/StatTile'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Table, THead, TH, TBody, TR, TD } from '../components/ui/Table'
import AdaptiveQuizModal from './student/AdaptiveQuizModal'

export default function StudentDashboardPage() {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    getProgress().then(setProgress)
  }, [])

  const totalWeak =
    progress?.courses.reduce((sum, c) => sum + c.weak_clo_count, 0) ?? 0

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-5">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">My Progress</h1>
          <p className="text-sm text-ink-500 mt-0.5">
            Your CLO attainment, score history, and adaptive practice
          </p>
        </div>

        {progress === null ? (
          <div className="flex justify-center py-24">
            <Spinner />
          </div>
        ) : progress.courses.length === 0 ? (
          <Card>
            <EmptyState
              title="No enrolled courses yet"
              description="Once you're enrolled in a course and scores are recorded, your attainment shows up here."
            />
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <StatTile
                label="Overall Attainment"
                value={`${progress.overall_average.toFixed(0)}%`}
                tone={progress.overall_average >= 50 ? 'success' : 'danger'}
              />
              <StatTile label="Enrolled Courses" value={progress.courses.length} />
              <StatTile
                label="Weak CLOs"
                value={totalWeak}
                tone={totalWeak > 0 ? 'danger' : 'success'}
              />
            </div>

            {progress.courses.map((course) => (
              <CourseProgressCard key={course.course_id} course={course} />
            ))}
          </>
        )}
      </main>
    </div>
  )
}

function CourseProgressCard({ course }) {
  const [scores, setScores] = useState(null)
  const [showScores, setShowScores] = useState(false)
  const [isQuizOpen, setIsQuizOpen] = useState(false)

  async function toggleScores() {
    const next = !showScores
    setShowScores(next)
    if (next && scores === null) {
      setScores(await getCourseScores(course.course_id))
    }
  }

  return (
    <Card>
      <CardHeader
        title={`${course.code} — ${course.name}`}
        description={`Semester ${course.semester} · Overall ${course.overall_average.toFixed(0)}%`}
        actions={
          <>
            <Badge tone={course.overall_average >= course.threshold ? 'success' : 'danger'}>
              {course.overall_average.toFixed(0)}%
            </Badge>
            <Button variant="secondary" size="sm" onClick={toggleScores}>
              {showScores ? 'Hide Scores' : 'Score History'}
            </Button>
            <Button size="sm" onClick={() => setIsQuizOpen(true)}>
              Practice Quiz
            </Button>
          </>
        }
      />
      <CardBody className="flex flex-col gap-5">
        <div>
          <h4 className="text-xs font-medium text-ink-500 uppercase tracking-wide mb-2">
            CLO Attainment
          </h4>
          <Table>
            <THead>
              <TR>
                <TH>CLO</TH>
                <TH>Title</TH>
                <TH className="w-40">Attainment</TH>
                <TH></TH>
              </TR>
            </THead>
            <TBody>
              {course.clo_progress.map((clo) => (
                <TR key={clo.clo_id}>
                  <TD className="font-medium">{clo.code}</TD>
                  <TD className="text-ink-500">{clo.title}</TD>
                  <TD>
                    <div className="flex items-center gap-2">
                      <div className="h-2 flex-1 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${clo.is_weak ? 'bg-danger-500' : 'bg-success-500'}`}
                          style={{ width: `${Math.min(clo.attainment_percentage, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs tabular-nums text-ink-500 w-10 text-right">
                        {clo.attainment_percentage.toFixed(0)}%
                      </span>
                    </div>
                  </TD>
                  <TD>
                    {clo.is_weak && <Badge tone="danger">Weak</Badge>}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </div>

        {showScores && (
          <div>
            <h4 className="text-xs font-medium text-ink-500 uppercase tracking-wide mb-2">
              Score History
            </h4>
            {scores === null ? (
              <div className="flex justify-center py-6">
                <Spinner />
              </div>
            ) : scores.items.length === 0 ? (
              <p className="text-sm text-ink-500">No assessments recorded yet.</p>
            ) : (
              <Table>
                <THead>
                  <TR>
                    <TH>Assessment</TH>
                    <TH>Type</TH>
                    <TH>Score</TH>
                    <TH>%</TH>
                  </TR>
                </THead>
                <TBody>
                  {scores.items.map((item) => (
                    <TR key={item.assessment_id}>
                      <TD className="font-medium">{item.title}</TD>
                      <TD className="text-ink-500 capitalize">{item.type}</TD>
                      <TD className="text-ink-500">
                        {item.obtained} / {item.total_marks}
                      </TD>
                      <TD className="text-ink-500">{item.percentage.toFixed(0)}%</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </div>
        )}
      </CardBody>

      <AdaptiveQuizModal
        isOpen={isQuizOpen}
        onClose={() => setIsQuizOpen(false)}
        course={course}
      />
    </Card>
  )
}
