import { useEffect, useMemo, useState } from 'react'
import type { EvaluateResponse } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { formatHours, formatMoney, formatMonth } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { progressFraction, statusChanges } from '../lib/story'
import { useCaseState } from '../state/caseState'
import { ProgressBar } from './ProgressBar'
import { InlineSkeleton, Skeleton } from './Skeleton'
import { StatusIcon } from './StatusIcon'

type MonthResult = EvaluateResponse['months'][number]
type MonthStatus = MonthResult['status']

// Color AND text (and an icon) so status never depends on color alone.
const STATUS_STYLE: Record<MonthStatus, { badge: string; border: string }> = {
  meets: { badge: 'bg-meets-soft text-meets border-meets', border: 'border-meets' },
  conditional: { badge: 'bg-conditional-soft text-conditional border-conditional', border: 'border-conditional' },
  short: { badge: 'bg-short-soft text-short border-short', border: 'border-line' },
}

// Path ids (from the ledger) that have a translated label; others show their id.
const PATH_LABELS: Record<string, MessageKey> = {
  hours_threshold: 'path_hours_threshold',
  income_threshold_cents: 'path_income_threshold_cents',
  school_half_time: 'path_school_half_time',
}

export function StatusBadge({ status }: { status: MonthStatus }) {
  const t = useT()
  const style = STATUS_STYLE[status]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold ${style.badge}`}>
      <StatusIcon kind={status} />
      {t(`status_${status}`)}
    </span>
  )
}

// Evaluations whose transition already ran, so a remount or re-render does
// not replay it. WeakSet: entries go away with the evaluation object.
const transitioned = new WeakSet<EvaluateResponse>()

// Work + volunteer hours (the ledger's meets path), summed in hundredths.
// Training hours count only conditionally on job_training_approved, so they are excluded.
function countedHours(m: MonthResult): number {
  return (Math.round(m.workHours * 100) + Math.round(m.volunteerHours * 100)) / 100
}

export function MonthCards({ evaluation }: { evaluation: EvaluateResponse }) {
  const t = useT()
  const { state } = useCaseState()
  const lang = state.caseInfo.lang
  const rules = state.rules
  const prior = state.priorEvaluation

  // Animate once per new evaluation: render the prior values first, then
  // switch to the new values two frames later so the CSS transitions run.
  const needsTransition = prior !== null && prior !== evaluation && !transitioned.has(evaluation)
  const [settledFor, setSettledFor] = useState<EvaluateResponse | null>(null)
  const settled = !needsTransition || settledFor === evaluation
  useEffect(() => {
    if (!needsTransition) return
    let second = 0
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => {
        transitioned.add(evaluation)
        setSettledFor(evaluation)
      })
    })
    return () => {
      cancelAnimationFrame(first)
      cancelAnimationFrame(second)
    }
  }, [evaluation, needsTransition])

  const changes = useMemo(
    () => (needsTransition || settledFor === evaluation ? statusChanges(prior, evaluation) : []),
    [needsTransition, settledFor, prior, evaluation],
  )
  const changedFrom = new Map(changes.map((c) => [c.month, c.from]))
  const priorMonths = new Map((prior?.months ?? []).map((m) => [m.month, m]))
  // Announced only after the swap, so the live region changes once.
  const announcement =
    settledFor === evaluation
      ? changes
          .map((c) => fill(t('statusAnnounce'), { month: formatMonth(c.month, lang), status: t(`status_${c.to}`) }))
          .join('. ')
      : ''
  const ruleText = (id: string) => rules?.unresolvedRules.find((r) => r.id === id)?.description ?? id
  const pathLabel = (id: string) => (PATH_LABELS[id] ? t(PATH_LABELS[id]) : id)

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">{t('monthsTitle')}</h3>
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {evaluation.months.map((m) => {
          const best = m.month === evaluation.bestMonth
          const counted = countedHours(m)
          const priorMonth = priorMonths.get(m.month)
          const fromStatus = changedFrom.get(m.month)
          const fraction = rules
            ? progressFraction(!settled && priorMonth ? countedHours(priorMonth) : counted, rules.thresholds.hours)
            : 0
          return (
            <li
              key={m.month}
              id={`month-${m.month}`}
              className={`rounded-[var(--radius-card)] border-2 bg-surface p-4 shadow-[var(--shadow-card)] ${best ? 'border-brand ring-2 ring-brand-soft' : STATUS_STYLE[m.status].border}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-base font-semibold">{formatMonth(m.month, lang)}</h4>
                {fromStatus ? (
                  // Cross-fade: prior badge fades out while the new one fades in.
                  <span className="inline-grid">
                    <span
                      aria-hidden={settled}
                      className={`[grid-area:1/1] transition-opacity delay-[400ms] duration-200 motion-reduce:transition-none ${settled ? 'opacity-0' : 'opacity-100'}`}
                    >
                      <StatusBadge status={fromStatus} />
                    </span>
                    <span
                      aria-hidden={!settled}
                      className={`[grid-area:1/1] transition-opacity delay-[400ms] duration-200 motion-reduce:transition-none ${settled ? 'opacity-100' : 'opacity-0'}`}
                    >
                      <StatusBadge status={m.status} />
                    </span>
                  </span>
                ) : (
                  <StatusBadge status={m.status} />
                )}
                {best && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand px-2.5 py-0.5 text-sm font-semibold text-white">
                    <StatusIcon kind="best" className="h-3.5 w-3.5" />
                    {t('bestMonth')}
                  </span>
                )}
              </div>

              <p className="mt-2 text-sm">{t(`statusHelp_${m.status}`)}</p>
              {m.status === 'conditional' && m.dependsOnUnresolved.length > 0 && (
                <ul className="mt-1 list-disc pl-5 text-sm text-conditional">
                  {m.dependsOnUnresolved.map((id) => (
                    <li key={id}>
                      {ruleText(id)} <span className="font-mono text-xs text-muted">({id})</span>
                    </li>
                  ))}
                </ul>
              )}

              {!rules && <Skeleton className="mt-3" />}
              {rules && (
                <div className="mt-3">
                  <ProgressBar
                    value={counted}
                    max={rules.thresholds.hours}
                    fraction={fraction}
                    label={fill(t('progressLabel'), {
                      counted: formatHours(counted, lang),
                      needed: formatHours(rules.thresholds.hours, lang),
                    })}
                  />
                </div>
              )}
              <dl className="tabular mt-3 space-y-1 text-sm">
                <div>
                  <dt className="sr-only">{t('field_hours')}</dt>
                  <dd className="font-medium">
                    {rules
                      ? fill(t('hoursTotal'), { hours: formatHours(counted, lang), needed: formatHours(rules.thresholds.hours, lang) })
                      : fill(t('hoursTotalNoTarget'), { hours: formatHours(counted, lang) })}
                  </dd>
                  <dd className="text-muted">
                    {fill(t('hoursBreakdown'), {
                      work: formatHours(m.workHours, lang),
                      volunteer: formatHours(m.volunteerHours, lang),
                    })}
                  </dd>
                  {m.trainingHours > 0 && (
                    <dd className="text-muted">{fill(t('trainingHours'), { hours: formatHours(m.trainingHours, lang) })}</dd>
                  )}
                  {m.schoolHalfTime && <dd className="text-muted">{t('schoolHalfTime')}</dd>}
                </div>
                <div>
                  <dd>{fill(t('incomeGross'), { amount: formatMoney(m.grossIncomeCents, lang) })}</dd>
                  <dd>{fill(t('incomeNet'), { amount: formatMoney(m.netIncomeCents, lang) })}</dd>
                  {!rules && (
                    <dd>
                      <InlineSkeleton className="w-32" />
                    </dd>
                  )}
                  {rules && (
                    <dd className="text-muted">{fill(t('incomeNeeded'), { amount: formatMoney(rules.thresholds.incomeCents, lang) })}</dd>
                  )}
                </div>
                {m.status !== 'meets' && (m.hoursShortfall > 0 || m.incomeShortfallCents > 0) && (
                  <div className="text-short">
                    {m.hoursShortfall > 0 && <dd>{fill(t('hoursShort'), { hours: formatHours(m.hoursShortfall, lang) })}</dd>}
                    {m.incomeShortfallCents > 0 && (
                      <dd>{fill(t('incomeShort'), { amount: formatMoney(m.incomeShortfallCents, lang) })}</dd>
                    )}
                  </div>
                )}
                {m.pathsMet.length > 0 && (
                  <dd className="text-meets">{fill(t('pathsMet'), { paths: m.pathsMet.map(pathLabel).join(', ') })}</dd>
                )}
                {m.excludedRecordIds.length > 0 && (
                  <dd className="font-medium text-conditional">{fill(t('excludedRecords'), { n: m.excludedRecordIds.length })}</dd>
                )}
              </dl>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
