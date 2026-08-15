import { useEffect } from 'react'

export default function Modal({ isOpen, onClose, title, description, children, width = 'max-w-lg' }) {
  useEffect(() => {
    if (!isOpen) return undefined
    function handleKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink-900/40" onClick={onClose} />
      <div
        className={`relative w-full ${width} rounded-xl bg-surface-raised shadow-[var(--shadow-elevation-3)]
          border border-border max-h-[90vh] flex flex-col`}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between gap-4 px-4 py-4 sm:px-5 border-b border-border shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-ink-900">{title}</h2>
            {description && <p className="mt-0.5 text-xs text-ink-500">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-400 hover:text-ink-700 rounded-md p-1 -m-1 shrink-0"
            aria-label="Close"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
        <div className="p-4 sm:p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

export function ModalFooter({ children }) {
  return <div className="flex items-center justify-end gap-2 pt-5 mt-5 border-t border-border">{children}</div>
}
