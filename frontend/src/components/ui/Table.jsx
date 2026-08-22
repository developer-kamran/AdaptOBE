import { forwardRef } from 'react'

export function Table({ children }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  )
}

export function THead({ children }) {
  return <thead>{children}</thead>
}

export function TH({ children, className = '' }) {
  return (
    <th
      className={`px-4 py-2.5 text-left text-xs font-medium text-ink-500 uppercase tracking-wide
        border-b border-border whitespace-nowrap ${className}`}
    >
      {children}
    </th>
  )
}

export function TBody({ children }) {
  return <tbody className="divide-y divide-border">{children}</tbody>
}

// forwardRef so drag-and-drop (dnd-kit's `useSortable`) can attach its node
// ref directly to the <tr>, e.g. via SortableRow.
export const TR = forwardRef(function TR({ children, className = '', ...props }, ref) {
  return (
    <tr ref={ref} className={`hover:bg-slate-50 transition-colors ${className}`} {...props}>
      {children}
    </tr>
  )
})

export function TD({ children, className = '' }) {
  return <td className={`px-4 py-2.5 text-ink-900 align-middle ${className}`}>{children}</td>
}
