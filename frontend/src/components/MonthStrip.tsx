import type { EvaluateResponse, MonthStatus } from '../api/client'
import { formatMonth, formatMonthShort } from '../i18n/format'
import { useT } from '../i18n/useT'
import { useCaseState } from '../state/caseState'
import { StatusIcon } from './StatusIcon'

// Icon + text + color so status never depends on color alone.
const STATUS_STYLE: Record<MonthStatus, { cell: string }> = {
  meets: { cell: 'border-meets bg-meets-soft text-meets' },
  conditional: { cell: 'border-conditional bg-conditional-soft text-conditional' },
  short: { cell: 'border-line bg-surface text-short' },
}

// One cell per month, in evaluation order. Each cell links to its month card.
export function MonthStrip({ evaluation }: { evaluation: EvaluateResponse }) {
  const t = useT()
  const { state } = useCaseState()
  const lang = state.caseInfo.lang
  return (
    <nav aria-label={t('monthStripLabel')}>
      <ol className="flex flex-wrap gap-2">
        {evaluation.months.map((m) => {
          const best = m.month === evaluation.bestMonth
          const style = STATUS_STYLE[m.status]
          return (
            <li key={m.month} className="min-w-[6.5rem] flex-1">
              <a
                href={`#month-${m.month}`}
                className={`flex h-full flex-col items-start gap-1 rounded-[var(--radius-card)] border-2 p-3 no-underline shadow-[var(--shadow-card)] hover:shadow-md ${style.cell} ${best ? 'ring-2 ring-brand' : ''}`}
              >
                <span className="font-semibold text-ink">
                  <span aria-hidden="true">{formatMonthShort(m.month, lang)}</span>
                  <span className="sr-only">{formatMonth(m.month, lang)}</span>
                </span>
                <span className="flex items-center gap-1 text-sm font-medium">
                  <StatusIcon kind={m.status} />
                  {t(`status_${m.status}`)}
                </span>
                {best && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand px-2 py-0.5 text-xs font-semibold text-white">
                    <StatusIcon kind="best" className="h-3 w-3" />
                    {t('bestMonth')}
                  </span>
                )}
              </a>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
