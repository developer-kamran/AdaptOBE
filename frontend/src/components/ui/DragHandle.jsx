// A small grip icon that is the *only* draggable surface of a sortable row
// (dnd-kit `attributes`/`listeners` are spread onto it) -- deliberately not
// the whole row, so existing row actions (Edit / Delete / Map to PLOs / ...)
// keep working with normal clicks. `touch-none` (CSS `touch-action: none`)
// stops the browser from trying to scroll the page while dragging on touch.
export default function DragHandle({ attributes, listeners }) {
  return (
    <button
      type="button"
      className="inline-flex items-center justify-center h-7 w-7 rounded-md text-ink-400
        hover:text-ink-700 hover:bg-slate-100 cursor-grab active:cursor-grabbing touch-none
        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      aria-label="Drag to reorder"
      {...attributes}
      {...listeners}
    >
      <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <circle cx="7" cy="5" r="1.3" />
        <circle cx="7" cy="10" r="1.3" />
        <circle cx="7" cy="15" r="1.3" />
        <circle cx="13" cy="5" r="1.3" />
        <circle cx="13" cy="10" r="1.3" />
        <circle cx="13" cy="15" r="1.3" />
      </svg>
    </button>
  )
}
