import { useT } from '../i18n/useT'
import { stageChips, type StageChipStatus } from '../lib/stages'
import type { CaseDocument } from '../state/caseState'
import { StatusIcon } from './StatusIcon'

// Icon + color per chip status. Status is always also shown as text.
const CHIP_STYLE: Record<StageChipStatus, { className: string }> = {
  working: { className: 'border-brand bg-brand-soft text-brand-strong' },
  ok: { className: 'border-meets bg-meets-soft text-meets' },
  warning: { className: 'border-conditional bg-conditional-soft text-conditional' },
  failed: { className: 'border-short bg-short-soft text-short' },
  skipped: { className: 'border-line bg-canvas text-muted' },
}

// Six stage chips for one document. The backend runs all stages in one request,
// so while it is in flight every chip shows "Working"; no per-stage progress is faked.
export function StageStrip({ document }: { document: CaseDocument }) {
  const t = useT()
  const { chips } = stageChips(document)

  return (
    <div className="mt-3">
      <ol aria-label={t('traceTitle')} className="flex flex-wrap items-center gap-y-2">
        {chips.map((chip, index) => {
          const style = CHIP_STYLE[chip.status]
          const statusText = chip.status === 'working' ? t('stageWorking') : t(`stageStatus_${chip.status}`)
          return (
            <li key={chip.stage} className="flex items-center">
              {index > 0 && (
                <span aria-hidden="true" className="px-1 text-muted">
                  →
                </span>
              )}
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm ${style.className}`}
              >
                <StatusIcon kind={chip.status} className="h-3.5 w-3.5" />
                <span className="font-medium">{t(`stage_${chip.stage}`)}</span>
                <span>· {statusText}</span>
              </span>
            </li>
          )
        })}
      </ol>
      {document.status === 'error' && document.error && (
        <p role="alert" className="mt-2 flex items-start gap-2 text-sm text-short">
          <StatusIcon kind="failed" className="mt-0.5 h-4 w-4" />
          <span>{document.error}</span>
        </p>
      )}
    </div>
  )
}
