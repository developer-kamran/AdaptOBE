import { useCallback, useEffect, useState } from 'react'
import { arrayMove } from '@dnd-kit/sortable'

// Frontend-only drag-and-drop reordering (CLOs / Assessments / Questions).
// There is deliberately no `display_order` column anywhere in the schema --
// this persists purely as an id ordering in localStorage, keyed per list, so
// a reorder survives a page refresh without any backend/API/migration
// change. See CHANGELOG.md ("Drag-and-drop reordering").
function readOrder(storageKey) {
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export default function useLocalOrder(storageKey) {
  const [order, setOrder] = useState(() => readOrder(storageKey))

  // Re-read if the caller switches to a different list (e.g. navigating
  // between courses re-uses this same hook instance's storageKey prop).
  useEffect(() => {
    setOrder(readOrder(storageKey))
  }, [storageKey])

  const persist = useCallback(
    (ids) => {
      setOrder(ids)
      try {
        localStorage.setItem(storageKey, JSON.stringify(ids))
      } catch {
        // Private-mode / quota-exceeded localStorage -- ordering just won't
        // survive a refresh; not worth surfacing an error for.
      }
    },
    [storageKey],
  )

  // Applies the stored id order to a freshly-loaded item list. Ids not yet
  // known (a newly-added row) are appended at the end, in API order. Stored
  // ids that no longer exist (a deleted row) are dropped silently.
  const applyOrder = useCallback(
    (items) => {
      if (!items) return items
      const byId = new Map(items.map((item) => [item.id, item]))
      const ordered = order.map((id) => byId.get(id)).filter(Boolean)
      const knownIds = new Set(ordered.map((item) => item.id))
      const rest = items.filter((item) => !knownIds.has(item.id))
      return [...ordered, ...rest]
    },
    [order],
  )

  // `items` must already be in the currently-displayed (post-applyOrder)
  // order -- this just moves `activeId` next to `overId` and persists the
  // resulting id list.
  const reorder = useCallback(
    (items, activeId, overId) => {
      const oldIndex = items.findIndex((item) => item.id === activeId)
      const newIndex = items.findIndex((item) => item.id === overId)
      if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return
      const next = arrayMove(items, oldIndex, newIndex)
      persist(next.map((item) => item.id))
    },
    [persist],
  )

  return { applyOrder, reorder }
}
