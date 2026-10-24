import type { EvaluateResponse, EvidenceRecord } from '../api/client'
import { formatHours, formatMonth } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { storyHeadline } from '../lib/story'
import { useCaseState } from '../state/caseState'
import { StatusIcon, type StatusIconKind } from './StatusIcon'

// The hero line of Results. Every number comes from the evaluation and records.
export function StoryHeadline({
  evaluation,
  records,
}: {
  evaluation: EvaluateResponse
  records: readonly EvidenceRecord[]
}) {
  const t = useT()
  const { state } = useCaseState()
  const lang = state.caseInfo.lang
  const story = storyHeadline(evaluation, records)
  const ruleText = (id: string) => state.rules?.unresolvedRules.find((r) => r.id === id)?.description ?? id

  let tone: string
  let icon: StatusIconKind
  let text: string
  if (story.kind === 'meets') {
    tone = 'border-meets bg-meets-soft text-meets'
    icon = 'meets'
    text = fill(t('headlineMeets'), {
      month: formatMonth(story.month, lang),
      hours: formatHours(story.hours, lang),
      n: story.sources,
    })
  } else if (story.kind === 'conditional') {
    tone = 'border-conditional bg-conditional-soft text-conditional'
    icon = 'conditional'
    text = fill(t('headlineConditional'), {
      month: formatMonth(story.month, lang),
      rules: story.ruleIds.map((id) => `${ruleText(id)} (${id})`).join('; '),
    })
  } else {
    tone = 'border-short bg-short-soft text-short'
    icon = 'short'
    text = t('headlineNone')
  }

  return (
    <section className={`rounded-[var(--radius-card)] border-2 p-5 shadow-[var(--shadow-card)] sm:p-6 ${tone}`}>
      <p className="flex items-start gap-3 text-2xl leading-snug font-semibold sm:text-3xl">
        <StatusIcon kind={icon} className="mt-0.5 h-8 w-8 sm:h-9 sm:w-9" />
        <span className="tabular">{text}</span>
      </p>
      <p className="mt-3 text-base text-ink">
        {t('appearsToShow')} {t('massHealthDecides')}
      </p>
    </section>
  )
}
