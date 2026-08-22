import { KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'

// Shared sensor config for drag-and-drop reordering lists. PointerSensor
// covers mouse/touch/pen through one unified Pointer Events path (dnd-kit's
// recommended approach -- native HTML5 drag-and-drop is deliberately not
// used here since it does not work on touch devices), with a small
// activation distance so a plain tap/click on the handle isn't mistaken for
// a drag. KeyboardSensor makes the same reordering possible via Space to
// pick up, Arrow keys to move, Space/Enter to drop.
export default function useDndSensors() {
  return useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
}
