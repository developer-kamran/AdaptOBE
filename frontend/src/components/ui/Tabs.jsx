export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex items-center gap-1 border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          onClick={() => onChange(tab.value)}
          className={`px-3.5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors
            ${
              active === tab.value
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-ink-500 hover:text-ink-700'
            }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
