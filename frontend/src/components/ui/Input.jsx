export default function Input({ label, error, className = '', id, ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink-700">
          {label}
        </label>
      )}
      <input
        id={id}
        className={`h-9 rounded-lg border px-3 text-sm text-ink-900 placeholder:text-ink-400
          transition-colors focus:border-brand-500
          ${error ? 'border-danger-500' : 'border-border-strong'} ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-danger-600">{error}</p>}
    </div>
  )
}
