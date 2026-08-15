import { useState } from 'react'
import Input from './Input'
import Button from './Button'

/**
 * Read-only display of a password fetched from the dedicated reveal
 * endpoint (never included in list/table responses). `password` is `null`
 * for accounts created before this feature or whose password was set
 * outside app code.
 */
export default function PasswordRevealField({ password, isLoading }) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-ink-700">Password</label>
      {isLoading ? (
        <p className="text-sm text-ink-500">Loading…</p>
      ) : password == null ? (
        <p className="text-sm text-ink-500">Not available</p>
      ) : (
        <div className="flex items-center gap-2">
          <Input
            type={visible ? 'text' : 'password'}
            value={password}
            readOnly
            className="flex-1 bg-slate-50"
          />
          <Button type="button" variant="secondary" size="sm" onClick={() => setVisible((v) => !v)}>
            {visible ? 'Hide' : 'Show'}
          </Button>
        </div>
      )}
    </div>
  )
}
