const TONES = {
  success: 'bg-success-50 text-success-700 ring-1 ring-inset ring-green-200',
  danger: 'bg-danger-50 text-danger-700 ring-1 ring-inset ring-red-200',
  warning: 'bg-warning-50 text-warning-700 ring-1 ring-inset ring-amber-200',
  brand: 'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200',
  neutral: 'bg-slate-100 text-ink-700 ring-1 ring-inset ring-slate-200',
}

export default function Badge({ tone = 'neutral', className = '', children }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium
        ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
