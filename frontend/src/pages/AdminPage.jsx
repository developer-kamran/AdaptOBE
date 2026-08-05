import { useState } from 'react'
import Navbar from '../components/Navbar'
import Tabs from '../components/ui/Tabs'
import { Card, CardBody } from '../components/ui/Card'
import DepartmentsPanel from './admin/DepartmentsPanel'
import ProgramsPanel from './admin/ProgramsPanel'
import PLOsPanel from './admin/PLOsPanel'
import UsersPanel from './admin/UsersPanel'

const TABS = [
  { value: 'departments', label: 'Departments', Component: DepartmentsPanel },
  { value: 'programs', label: 'Programmes', Component: ProgramsPanel },
  { value: 'plos', label: 'PLOs', Component: PLOsPanel },
  { value: 'users', label: 'Users', Component: UsersPanel },
]

export default function AdminPage() {
  const [active, setActive] = useState('departments')
  const ActivePanel = TABS.find((tab) => tab.value === active).Component

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 flex flex-col gap-5">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Admin Panel</h1>
          <p className="text-sm text-ink-500 mt-0.5">
            Manage departments, programmes, PLOs and user accounts
          </p>
        </div>

        <Tabs tabs={TABS} active={active} onChange={setActive} />

        <Card>
          <CardBody>
            <ActivePanel />
          </CardBody>
        </Card>
      </main>
    </div>
  )
}
