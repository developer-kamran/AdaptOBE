export default function Textarea({ label, error, className = '', id, ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink-700">
          {label}
        </label>
      )}
      <textarea
        id={id}
        className={`rounded-lg border px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400
          transition-colors focus:border-brand-500 resize-y
          ${error ? 'border-danger-500' : 'border-border-strong'} ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-danger-600">{error}</p>}
    </div>
  )
}
