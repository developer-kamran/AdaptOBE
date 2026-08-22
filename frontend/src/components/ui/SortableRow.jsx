import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { TR } from './Table'

// A <TR> that participates in dnd-kit drag-and-drop reordering. `children`
// is a render function so callers can pass the drag handle's `attributes`/
// `listeners` into a `DragHandle` cell without making the whole row
// draggable (see DragHandle.jsx).
export default function SortableRow({ id, children, className = '', ...rest }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <TR
      ref={setNodeRef}
      style={style}
      className={`${className} ${isDragging ? 'relative z-10 bg-slate-50 shadow-[var(--shadow-elevation-2)]' : ''}`}
      {...rest}
    >
      {children({ attributes, listeners, isDragging })}
    </TR>
  )
}
