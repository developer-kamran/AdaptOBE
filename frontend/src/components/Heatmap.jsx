import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Badge from './ui/Badge'

const STRENGTH_STYLE = {
  1: 'bg-brand-100 text-brand-700',
  2: 'bg-brand-300 text-brand-900',
  3: 'bg-brand-600 text-white',
}

const STRENGTH_LABEL = { 1: 'Weak', 2: 'Moderate', 3: 'Strong' }

function averageTone(value, threshold) {
  return value >= threshold ? 'success' : 'danger'
}

// Hover tooltip (no click needed) for the CLO/PLO code labels -- distinct
// from InfoTooltip, which is click-to-open for optional supplementary detail
// elsewhere. Portal'd to <body> and positioned from the trigger's own
// bounding rect, because the row labels live inside `sticky` table cells:
// each sticky cell is its own stacking context, so a same-DOM-subtree
// absolutely-positioned tooltip can get painted *behind* the next sticky row
// no matter how high its z-index goes. Escaping to the body sidesteps that
// entirely.
function HoverLabel({ label, tooltip, align = 'center' }) {
  const triggerRef = useRef(null)
  const [pos, setPos] = useState(null)

  function show() {
    const rect = triggerRef.current?.getBoundingClientRect()
    if (!rect) return
    setPos({ top: rect.bottom + 6, left: align === 'left' ? rect.left : rect.left + rect.width / 2 })
  }

  return (
    <span
      ref={triggerRef}
      className="inline-block cursor-default"
      onMouseEnter={show}
      onMouseLeave={() => setPos(null)}
    >
      {label}
      {pos &&
        createPortal(
          <div
            role="tooltip"
            style={{
              position: 'fixed',
              top: pos.top,
              left: pos.left,
              transform: align === 'left' ? 'none' : 'translateX(-50%)',
            }}
            className="z-50 w-max max-w-[16rem] rounded-lg bg-ink-900 text-white text-xs leading-relaxed
              px-3 py-2 shadow-[var(--shadow-elevation-3)] pointer-events-none"
          >
            {tooltip}
          </div>,
          document.body
        )}
    </span>
  )
}

/**
 * CLO (rows) x PLO (columns) mapping-strength grid, with each axis's class
 * average shown as a header row/column so attainment and mapping strength
 * read together at a glance.
 */
export default function Heatmap({ report }) {
  const { clo_attainment: clos, plo_attainment: plos, heatmap, threshold } = report

  if (clos.length === 0) {
    return <p className="text-sm text-ink-500 py-8 text-center">No CLOs defined for this course yet.</p>
  }
  if (plos.length === 0) {
    return (
      <p className="text-sm text-ink-500 py-8 text-center">
        No PLOs are mapped for this course's program yet.
      </p>
    )
  }

  const strengthByPair = new Map(heatmap.map((cell) => [`${cell.clo_id}:${cell.plo_id}`, cell.strength]))

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-sm min-w-full">
        <thead>
          <tr>
            <th className="sticky left-0 bg-surface-raised text-left font-medium text-ink-500 text-xs uppercase tracking-wide px-3 py-2 border-b border-r border-border">
              CLO \ PLO
            </th>
            {plos.map((plo) => (
              <th
                key={plo.plo_id}
                className="px-3 py-2 border-b border-border text-center font-medium text-ink-700 whitespace-nowrap min-w-[84px]"
              >
                <HoverLabel label={plo.code} tooltip={plo.title} />
              </th>
            ))}
            <th className="px-3 py-2 border-b border-l border-border text-center font-medium text-ink-500 text-xs uppercase tracking-wide whitespace-nowrap">
              Class Avg
            </th>
          </tr>
        </thead>
        <tbody>
          {clos.map((clo) => (
            <tr key={clo.clo_id}>
              <th className="sticky left-0 bg-surface-raised text-left font-medium text-ink-900 px-3 py-2 border-r border-b border-border whitespace-nowrap">
                <HoverLabel
                  label={clo.code}
                  tooltip={clo.bloom_level ? `${clo.title} — ${clo.bloom_level}` : clo.title}
                  align="left"
                />
              </th>
              {plos.map((plo) => {
                const strength = strengthByPair.get(`${clo.clo_id}:${plo.plo_id}`)
                return (
                  <td key={plo.plo_id} className="border-b border-border p-1.5 text-center">
                    {strength ? (
                      <div
                        title={`${STRENGTH_LABEL[strength]} (${strength})`}
                        className={`h-8 w-full rounded-md flex items-center justify-center font-semibold text-xs ${STRENGTH_STYLE[strength]}`}
                      >
                        {STRENGTH_LABEL[strength]}
                      </div>
                    ) : (
                      <div className="h-8 w-full rounded-md flex items-center justify-center text-ink-400 text-xs bg-slate-50">
                        –
                      </div>
                    )}
                  </td>
                )
              })}
              <td className="border-b border-l border-border px-3 py-2 text-center">
                <Badge tone={averageTone(clo.class_average, threshold)}>
                  {clo.class_average.toFixed(1)}%
                </Badge>
              </td>
            </tr>
          ))}
          <tr>
            <th className="sticky left-0 bg-surface-raised text-left font-medium text-ink-500 text-xs uppercase tracking-wide px-3 py-2 border-r border-t border-border">
              Class Avg
            </th>
            {plos.map((plo) => (
              <td key={plo.plo_id} className="border-t border-border px-3 py-2 text-center">
                <Badge tone={averageTone(plo.class_average, threshold)}>
                  {plo.class_average.toFixed(1)}%
                </Badge>
              </td>
            ))}
            <td className="border-t border-l border-border" />
          </tr>
        </tbody>
      </table>
    </div>
  )
}
