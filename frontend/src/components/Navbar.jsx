import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Button from './ui/Button'
import Badge from './ui/Badge'

const NAV_LINK_CLASS = ({ isActive }) =>
  `text-sm font-medium px-1 pb-0.5 border-b-2 transition-colors ${
    isActive ? 'border-brand-600 text-ink-900' : 'border-transparent text-ink-500 hover:text-ink-700'
  }`

const MOBILE_NAV_LINK_CLASS = ({ isActive }) =>
  `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-ink-700 hover:bg-slate-100'
  }`

function NavLinks({ user }) {
  return (
    <>
      {(user.role === 'faculty' || user.role === 'sub_admin') && (
        <NavLink to="/courses" className={NAV_LINK_CLASS}>
          Courses
        </NavLink>
      )}
      {user.role === 'faculty' && (
        <NavLink to="/dashboard" className={NAV_LINK_CLASS}>
          Dashboard
        </NavLink>
      )}
      {(user.role === 'super_admin' || user.role === 'sub_admin') && (
        <NavLink to="/admin" className={NAV_LINK_CLASS}>
          Admin Panel
        </NavLink>
      )}
    </>
  )
}

function MobileNavLinks({ user, onNavigate }) {
  return (
    <>
      {(user.role === 'faculty' || user.role === 'sub_admin') && (
        <NavLink to="/courses" className={MOBILE_NAV_LINK_CLASS} onClick={onNavigate}>
          Courses
        </NavLink>
      )}
      {user.role === 'faculty' && (
        <NavLink to="/dashboard" className={MOBILE_NAV_LINK_CLASS} onClick={onNavigate}>
          Dashboard
        </NavLink>
      )}
      {(user.role === 'super_admin' || user.role === 'sub_admin') && (
        <NavLink to="/admin" className={MOBILE_NAV_LINK_CLASS} onClick={onNavigate}>
          Admin Panel
        </NavLink>
      )}
    </>
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="border-b border-border bg-surface-raised shrink-0 relative z-40">
      <div className="h-14 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-md bg-brand-600 text-white font-bold text-sm flex items-center justify-center shrink-0">
              A
            </div>
            <span className="text-sm font-semibold text-ink-900">AdaptOBE</span>
          </div>

          {user && (
            <nav className="hidden md:flex items-center gap-5">
              <NavLinks user={user} />
            </nav>
          )}
        </div>

        {user && (
          <>
            <div className="hidden md:flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-medium text-ink-900 leading-tight">{user.full_name}</p>
                <p className="text-xs text-ink-500 leading-tight">{user.email}</p>
              </div>
              <Badge tone="brand" className="capitalize">
                {user.role.replace('_', ' ')}
              </Badge>
              <Button variant="ghost" size="sm" onClick={logout}>
                Sign out
              </Button>
            </div>

            <button
              type="button"
              className="md:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg text-ink-700 hover:bg-slate-100 shrink-0"
              onClick={() => setIsMenuOpen((open) => !open)}
              aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={isMenuOpen}
            >
              {isMenuOpen ? (
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
          </>
        )}
      </div>

      {user && isMenuOpen && (
        <div className="md:hidden border-t border-border bg-surface-raised px-4 py-3 flex flex-col gap-3 shadow-[var(--shadow-elevation-2)]">
          <nav className="flex flex-col gap-1">
            <MobileNavLinks user={user} onNavigate={() => setIsMenuOpen(false)} />
          </nav>
          <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink-900 leading-tight truncate">{user.full_name}</p>
              <p className="text-xs text-ink-500 leading-tight break-all">{user.email}</p>
              <Badge tone="brand" className="capitalize mt-1.5">
                {user.role.replace('_', ' ')}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0"
              onClick={() => {
                setIsMenuOpen(false)
                logout()
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      )}
    </header>
  )
}
