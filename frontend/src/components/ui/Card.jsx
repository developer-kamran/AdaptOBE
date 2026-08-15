export function Card({ className = '', children, ...props }) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface-raised
        shadow-[var(--shadow-elevation-1)] ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, description, actions, className = '' }) {
  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 px-4 py-4 sm:px-5 border-b border-border ${className}`}
    >
      <div>
        <h2 className="text-sm font-semibold text-ink-900">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-ink-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

export function CardBody({ className = '', children }) {
  return <div className={`p-4 sm:p-5 ${className}`}>{children}</div>
}
