import type { DocumentResult } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { fill, useT } from '../i18n/useT'
import { stageChips } from '../lib/stages'
import type { CaseDocument } from '../state/caseState'
import { StatusIcon } from './StatusIcon'

type Stage = DocumentResult['pipeline'][number]

const STATUS_STYLE: Record<Stage['status'], { className: string }> = {
  ok: { className: 'text-meets' },
  warning: { className: 'text-conditional' },
  failed: { className: 'text-short' },
  skipped: { className: 'text-muted' },
}

// Known backend warnings get a translated message; anything else is shown as sent.
const KNOWN_WARNINGS: Record<string, MessageKey> = {
  'Could not recognize this document. Choose its type.': 'warningUnknownType',
  'Enter the values manually.': 'warningManualEntry',
}

// Detail view under the StageStrip: durations, detail, extractor, warnings.
// Opens by default when stageChips() says a stage or the result has a problem.
export function PipelineTrace({ document }: { document: CaseDocument }) {
  const t = useT()
  const result = document.result
  if (!result) return null
  const { openDetails } = stageChips(document)

  return (
    <details className="mt-3 rounded-[var(--radius-card)] border border-line bg-canvas" open={openDetails}>
      <summary className="cursor-pointer px-3 py-2 font-medium">{t('traceTitle')}</summary>
      <div className="px-3 pb-3">
        <ol className="space-y-1">
          {result.pipeline.map((stage) => {
            const style = STATUS_STYLE[stage.status]
            return (
              <li key={stage.stage} className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <StatusIcon kind={stage.status} className={`h-4 w-4 self-center ${style.className}`} />
                <span className="font-medium">{t(`stage_${stage.stage}`)}</span>
                <span className={style.className}>{t(`stageStatus_${stage.status}`)}</span>
                <span className="text-muted">{fill(t('durationMs'), { ms: stage.durationMs })}</span>
                {stage.detail && <span className="basis-full pl-6 text-muted">{stage.detail}</span>}
              </li>
            )
          })}
        </ol>
        <p className="mt-2 text-sm">
          <span className="font-medium">{t('extractorLabel')}:</span> {t(`extractor_${result.extractor}`)}
        </p>
        {result.warnings.length > 0 && (
          <div className="mt-2 text-sm">
            <p className="font-medium text-conditional">{t('warningsLabel')}</p>
            <ul className="list-disc pl-5">
              {result.warnings.map((warning) => {
                const key = KNOWN_WARNINGS[warning]
                return <li key={warning}>{key ? t(key) : warning}</li>
              })}
            </ul>
          </div>
        )}
      </div>
    </details>
  )
}
