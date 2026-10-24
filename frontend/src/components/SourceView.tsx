import { useEffect, useId, useRef, type KeyboardEvent } from 'react'
import { X } from 'lucide-react'
import type { PageView } from '../api/client'
import { fill, useT } from '../i18n/useT'
import { findLine } from '../lib/highlight'

interface SourceViewProps {
  fieldLabel: string
  fileName: string
  page: PageView | null
  evidence: string | null | undefined
  onClose: () => void
}

const FOCUSABLE = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'

// Modal that shows the page picture with the field's evidence line highlighted.
export function SourceView({ fieldLabel, fileName, page, evidence, onClose }: SourceViewProps) {
  const t = useT()
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  // Focus the close button on open; return focus to the trigger on close.
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeRef.current?.focus()
    return () => trigger?.focus()
  }, [])

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose()
      return
    }
    if (e.key !== 'Tab' || !dialogRef.current) return
    const items = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE))
    if (items.length === 0) return
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  const lines = page?.lines ?? []
  const index = findLine(lines, evidence)
  const box = index === null ? null : lines[index].box
  const image = page?.imageDataUrl ?? null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/60 p-2 sm:items-center sm:p-6"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className="w-full max-w-3xl rounded-[var(--radius-card)] bg-surface p-4 shadow-[var(--shadow-card)] motion-safe:transition-opacity"
      >
        <div className="mb-3 flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 id={titleId} className="text-lg font-semibold text-ink">
              {fieldLabel}
            </h2>
            <p className="text-sm break-all text-muted">
              {fileName}
              {page ? ` · ${t('colPage')} ${page.page}` : ''}
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1 rounded-md border border-line px-3 py-1.5 text-sm font-semibold text-ink hover:bg-canvas"
          >
            <X aria-hidden="true" focusable="false" className="h-4 w-4" />
            {t('close')}
          </button>
        </div>
        {evidence && <p className="mb-3 rounded-md bg-canvas p-2 font-mono text-xs break-words text-muted">{evidence}</p>}
        {image ? (
          <>
            {box === null && (
              <p role="status" className="mb-3 rounded-md bg-conditional-soft p-2 text-sm font-medium text-conditional">
                {t('lineNotFound')}
              </p>
            )}
            <div className="relative w-full rounded-md border border-line">
              <img src={image} alt={fill(t('documentPreview'), { name: fileName })} className="block h-auto w-full rounded-md" />
              {box && (
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute rounded-sm bg-conditional/25 outline-3 outline-conditional"
                  style={{
                    left: `${box.x0 * 100}%`,
                    top: `${box.y0 * 100}%`,
                    width: `${(box.x1 - box.x0) * 100}%`,
                    height: `${(box.y1 - box.y0) * 100}%`,
                  }}
                />
              )}
            </div>
          </>
        ) : (
          <p role="status" className="rounded-md bg-canvas p-3 text-sm text-muted">
            {t('noPageImage')}
          </p>
        )}
      </div>
    </div>
  )
}
