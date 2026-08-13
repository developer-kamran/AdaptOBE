import { useState } from 'react'
import Navbar from '../components/Navbar'
import Tabs from '../components/ui/Tabs'
import { Card, CardBody } from '../components/ui/Card'
import { useAuth } from '../context/AuthContext'
import DepartmentsPanel from './admin/DepartmentsPanel'
import ProgramsPanel from './admin/ProgramsPanel'
import PLOsPanel from './admin/PLOsPanel'
import UsersPanel from './admin/UsersPanel'
import StudentsPanel from './admin/StudentsPanel'
import FacultyPanel from './admin/FacultyPanel'

const SUPER_ADMIN_TABS = [
  { value: 'departments', label: 'Departments', Component: DepartmentsPanel },
  { value: 'sub-admins', label: 'Sub-Admins', Component: UsersPanel },
]

const SUB_ADMIN_TABS = [
  { value: 'programs', label: 'Programmes', Component: ProgramsPanel },
  { value: 'plos', label: 'PLOs', Component: PLOsPanel },
  { value: 'students', label: 'Students', Component: StudentsPanel },
  { value: 'faculty', label: 'Faculty', Component: FacultyPanel },
]

const COPY = {
  super_admin: 'Manage departments and sub-admin accounts',
  sub_admin: "Manage your department's programmes, PLOs, faculty, and students",
}

export default function AdminPage() {
  const { user } = useAuth()
  const tabs = user.role === 'super_admin' ? SUPER_ADMIN_TABS : SUB_ADMIN_TABS
  const [active, setActive] = useState(tabs[0].value)
  const ActivePanel = (tabs.find((tab) => tab.value === active) ?? tabs[0]).Component

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-5">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Admin Panel</h1>
          <p className="text-sm text-ink-500 mt-0.5">{COPY[user.role]}</p>
        </div>

        <Tabs tabs={tabs} active={active} onChange={setActive} />

        <Card>
          <CardBody>
            <ActivePanel />
          </CardBody>
        </Card>
      </main>
    </div>
  )
}
