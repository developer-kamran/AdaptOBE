export default function Select({ label, className = '', id, children, ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink-700">
          {label}
        </label>
      )}
      <select
        id={id}
        className={`h-9 rounded-lg border border-border-strong bg-white px-3 text-sm text-ink-900
          transition-colors focus:border-brand-500 ${className}`}
        {...props}
      >
        {children}
      </select>
    </div>
  )
}
