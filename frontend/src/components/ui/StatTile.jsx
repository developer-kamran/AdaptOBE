export default function StatTile({ label, value, hint, tone = 'neutral' }) {
  const valueTone = {
    neutral: 'text-ink-900',
    success: 'text-success-600',
    danger: 'text-danger-600',
  }[tone]

  return (
    <div className="rounded-xl border border-border bg-surface-raised px-4 py-3.5 shadow-[var(--shadow-elevation-1)]">
      <p className="text-xs font-medium text-ink-500 uppercase tracking-wide">{label}</p>
      <p className={`mt-1.5 text-2xl font-semibold tabular-nums ${valueTone}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-400">{hint}</p>}
    </div>
  )
}
