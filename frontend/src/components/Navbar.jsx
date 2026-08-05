import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Button from './ui/Button'
import Badge from './ui/Badge'

const NAV_LINK_CLASS = ({ isActive }) =>
  `text-sm font-medium px-1 pb-0.5 border-b-2 transition-colors ${
    isActive ? 'border-brand-600 text-ink-900' : 'border-transparent text-ink-500 hover:text-ink-700'
  }`

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="h-14 border-b border-border bg-surface-raised px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-md bg-brand-600 text-white font-bold text-sm flex items-center justify-center">
            A
          </div>
          <span className="text-sm font-semibold text-ink-900">AdaptOBE</span>
        </div>

        {user && (
          <nav className="flex items-center gap-5">
            {(user.role === 'faculty' || user.role === 'admin') && (
              <>
                <NavLink to="/courses" className={NAV_LINK_CLASS}>
                  Courses
                </NavLink>
                <NavLink to="/dashboard" className={NAV_LINK_CLASS}>
                  Dashboard
                </NavLink>
              </>
            )}
            {user.role === 'admin' && (
              <NavLink to="/admin" className={NAV_LINK_CLASS}>
                Admin Panel
              </NavLink>
            )}
          </nav>
        )}
      </div>

      {user && (
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-ink-900 leading-tight">{user.full_name}</p>
            <p className="text-xs text-ink-500 leading-tight">{user.email}</p>
          </div>
          <Badge tone="brand" className="capitalize">
            {user.role}
          </Badge>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      )}
    </header>
  )
}
