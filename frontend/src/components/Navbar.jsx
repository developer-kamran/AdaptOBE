import { useAuth } from '../context/AuthContext'
import Button from './ui/Button'
import Badge from './ui/Badge'

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="h-14 border-b border-border bg-surface-raised px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-2.5">
        <div className="h-7 w-7 rounded-md bg-brand-600 text-white font-bold text-sm flex items-center justify-center">
          A
        </div>
        <span className="text-sm font-semibold text-ink-900">AdaptOBE</span>
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
