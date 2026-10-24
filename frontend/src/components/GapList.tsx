import type { EvaluateResponse } from '../api/client'
import { formatMonth } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { useCaseState } from '../state/caseState'
import { StatusIcon } from './StatusIcon'

export function GapList({ gaps }: { gaps: EvaluateResponse['gaps'] }) {
  const t = useT()
  const { state } = useCaseState()
  const lang = state.caseInfo.lang

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">{t('gapsTitle')}</h3>
      {gaps.length === 0 ? (
        <p className="text-muted">{t('noGaps')}</p>
      ) : (
        <ul className="space-y-2">
          {gaps.map((gap, i) => (
            <li key={`${gap.month}-${gap.kind}-${gap.ruleId ?? ''}-${i}`} className="flex gap-2 rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)]">
              <StatusIcon kind="warning" className="mt-0.5 h-4 w-4 text-conditional" />
              <div className="min-w-0">
              <p className="text-sm font-semibold text-muted">{formatMonth(gap.month, lang)}</p>
              <p className="tabular">{gap.message}</p>
              {gap.suggestedDocTypes.length > 0 && (
                <p className="mt-1 text-sm text-muted">
                  {fill(t('suggestedDocs'), { docs: gap.suggestedDocTypes.map((d) => t(`docType_${d}`)).join(', ') })}
                </p>
              )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
