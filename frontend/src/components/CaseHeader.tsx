import type { ReactNode, Ref } from 'react'
import { useT } from '../i18n/useT'
import { caseSources } from '../lib/story'
import { useCaseState } from '../state/caseState'

// Person-first case header shown at the top of every case step (Requirement 2).
export function CaseHeader({
  isSample,
  headingRef,
  deadlineSlot,
}: {
  isSample: boolean
  headingRef?: Ref<HTMLHeadingElement>
  // CasePage passes <DeadlineChip /> here.
  deadlineSlot?: ReactNode
}) {
  const t = useT()
  const { state } = useCaseState()
  const name = state.caseInfo.clientName.trim()
  // Before the client name is known (new case, or sample still loading), show the page title.
  const title = name || (isSample ? t('sampleCaseTitle') : t('caseTitle'))
  const sources = isSample ? [] : caseSources(state.records)
  const places = isSample ? t('sampleStoryPlaces') : sources.join(' · ')

  return (
    <header className="space-y-2 rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 ref={headingRef} tabIndex={-1} className="min-w-0 break-words text-2xl font-bold text-ink">
          {title}
        </h1>
        {deadlineSlot}
      </div>
      {places && <p className="break-words font-medium text-ink">{places}</p>}
      {isSample && <p className="text-muted">{t('sampleStoryIntro')}</p>}
    </header>
  )
}
