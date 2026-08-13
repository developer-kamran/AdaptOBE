import { useEffect, useRef, useState } from 'react'

// Small "ⓘ" affordance that reveals a short explanatory popover on click.
// Used wherever an AI-derived result (CLO<->PLO / question<->CLO matching)
// is shown as a plain-language label -- the popover is where the technical
// detail (e.g. the raw similarity score) lives, kept out of the primary UI.
export default function InfoTooltip({ children, className = '' }) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return undefined
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false)
    }
    function handleKey(e) {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [isOpen])

  return (
    <span className={`relative inline-flex ${className}`} ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-label="More information"
        aria-expanded={isOpen}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full text-ink-400
          hover:text-brand-600 hover:bg-brand-50 transition-colors"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
          <path
            fillRule="evenodd"
            d="M18 10A8 8 0 112 10a8 8 0 0116 0zM9 9a1 1 0 011-1h.01a1 1 0 010 2H10a1 1 0 01-1-1zm1 3a1 1 0 100 2 1 1 0 000-2zm0-6a1 1 0 100 2 1 1 0 000-2z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {isOpen && (
        <div
          role="tooltip"
          className="absolute z-10 top-6 left-1/2 -translate-x-1/2 w-[min(16rem,calc(100vw-2.5rem))] rounded-lg
            bg-ink-900 text-white text-xs leading-relaxed px-3 py-2 shadow-[var(--shadow-elevation-3)]"
        >
          {children}
        </div>
      )}
    </span>
  )
}
