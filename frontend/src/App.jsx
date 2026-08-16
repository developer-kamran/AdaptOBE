import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AdminPage from './pages/AdminPage'
import CoursesPage from './pages/CoursesPage'
import CourseDetailPage from './pages/CourseDetailPage'
import AssessmentDetailPage from './pages/AssessmentDetailPage'
import StudentDashboardPage from './pages/StudentDashboardPage'
import Spinner from './components/ui/Spinner'

function HomeRedirect() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'super_admin' || user.role === 'sub_admin') {
    return <Navigate to="/admin" replace />
  }
  if (user.role === 'faculty') return <Navigate to="/dashboard" replace />
  if (user.role === 'student') return <Navigate to="/student" replace />
  return <Navigate to="/courses" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute roles={['faculty']}>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={['super_admin', 'sub_admin']}>
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses"
            element={
              <ProtectedRoute roles={['faculty', 'sub_admin']}>
                <CoursesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId"
            element={
              <ProtectedRoute roles={['faculty']}>
                <CourseDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/assessments/:assessmentId"
            element={
              <ProtectedRoute roles={['faculty']}>
                <AssessmentDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student"
            element={
              <ProtectedRoute roles={['student']}>
                <StudentDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<HomeRedirect />} />
          <Route path="*" element={<HomeRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
