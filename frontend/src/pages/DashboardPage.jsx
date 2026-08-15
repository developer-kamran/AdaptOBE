import { useCallback, useEffect, useState } from 'react'
import { listMyCourses } from '../api/courses'
import {
  exportCourseExcel,
  exportCoursePdf,
  getCourseAttainment,
  recalculateCourseAttainment,
} from '../api/attainment'
import { useCourseWebSocket } from '../hooks/useCourseWebSocket'
import Navbar from '../components/Navbar'
import Heatmap from '../components/Heatmap'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import Spinner from '../components/ui/Spinner'
import StatTile from '../components/ui/StatTile'
import Badge from '../components/ui/Badge'
import EmptyState from '../components/ui/EmptyState'
import { Card, CardBody, CardHeader } from '../components/ui/Card'

export default function DashboardPage() {
  const [courses, setCourses] = useState(null)
  const [selectedCourseId, setSelectedCourseId] = useState(null)
  const [report, setReport] = useState(null)
  const [isReportLoading, setIsReportLoading] = useState(false)
  const [isExporting, setIsExporting] = useState(null)
  const [justUpdated, setJustUpdated] = useState(false)

  useEffect(() => {
    ;(async () => {
      const data = await listMyCourses()
      setCourses(data)
      if (data.length > 0) setSelectedCourseId(data[0].id)
    })()
  }, [])

  const loadReport = useCallback(async (courseId) => {
    setIsReportLoading(true)
    try {
      setReport(await getCourseAttainment(courseId))
    } finally {
      setIsReportLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedCourseId) loadReport(selectedCourseId)
  }, [selectedCourseId, loadReport])

  const handleLiveUpdate = useCallback(
    (event) => {
      if (event.type === 'attainment.recalculated' && event.course_id === selectedCourseId) {
        loadReport(selectedCourseId)
        setJustUpdated(true)
        setTimeout(() => setJustUpdated(false), 2500)
      }
    },
    [selectedCourseId, loadReport],
  )

  const { isConnected } = useCourseWebSocket(selectedCourseId, handleLiveUpdate)

  async function handleExport(format) {
    setIsExporting(format)
    try {
      if (format === 'pdf') await exportCoursePdf(selectedCourseId)
      else await exportCourseExcel(selectedCourseId)
    } finally {
      setIsExporting(null)
    }
  }

  async function handleRecalculate() {
    setIsReportLoading(true)
    try {
      setReport(await recalculateCourseAttainment(selectedCourseId))
    } finally {
      setIsReportLoading(false)
    }
  }

  const selectedCourse = courses?.find((c) => c.id === selectedCourseId)
  const achievedCount = report?.clo_attainment.filter((c) => c.is_achieved).length ?? 0

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-semibold text-ink-900">Faculty Dashboard</h1>
            <p className="text-sm text-ink-500 mt-0.5">
              CLO/PLO attainment for the courses you own
            </p>
          </div>

          {courses && courses.length > 0 && (
            <div className="w-full sm:w-64">
              <Select
                value={selectedCourseId ?? ''}
                onChange={(e) => setSelectedCourseId(Number(e.target.value))}
              >
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </Select>
            </div>
          )}
        </div>

        {courses === null ? (
          <div className="flex justify-center py-24">
            <Spinner />
          </div>
        ) : courses.length === 0 ? (
          <Card>
            <EmptyState
              title="No courses yet"
              description="Courses you create will show up here with their CLO/PLO attainment."
            />
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatTile label="Enrolled Students" value={report?.student_count ?? '—'} />
              <StatTile label="Threshold" value={report ? `${report.threshold.toFixed(0)}%` : '—'} />
              <StatTile
                label="CLOs Achieved"
                value={report ? `${achievedCount} / ${report.clo_attainment.length}` : '—'}
                tone={report && achievedCount === report.clo_attainment.length ? 'success' : 'neutral'}
              />
              <StatTile
                label="Live Connection"
                value={
                  <Badge tone={isConnected ? 'success' : 'neutral'}>
                    {isConnected ? 'Connected' : 'Offline'}
                  </Badge>
                }
              />
            </div>

            <Card>
              <CardHeader
                title="CLO × PLO Attainment Heatmap"
                description={selectedCourse ? `${selectedCourse.code} — ${selectedCourse.name}` : undefined}
                actions={
                  <>
                    {justUpdated && (
                      <Badge tone="success" className="animate-pulse">
                        Updated live
                      </Badge>
                    )}
                    <Button variant="secondary" size="sm" onClick={handleRecalculate} isLoading={isReportLoading}>
                      Recalculate
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleExport('excel')}
                      isLoading={isExporting === 'excel'}
                      disabled={isExporting !== null}
                    >
                      Export Excel
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleExport('pdf')}
                      isLoading={isExporting === 'pdf'}
                      disabled={isExporting !== null}
                    >
                      Export PDF
                    </Button>
                  </>
                }
              />
              <CardBody>
                {isReportLoading && !report ? (
                  <div className="flex justify-center py-16">
                    <Spinner />
                  </div>
                ) : report ? (
                  <Heatmap report={report} />
                ) : null}
              </CardBody>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}
