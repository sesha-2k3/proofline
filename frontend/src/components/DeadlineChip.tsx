import { formatDate } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { deadlineView, localTodayIso, type DeadlineView } from '../lib/deadline'
import { useCaseState } from '../state/caseState'
import { InlineSkeleton } from './Skeleton'
import { StatusIcon } from './StatusIcon'


// Response deadline shown on every case step (Requirement 3).
export function DeadlineChip({ isSample }: { isSample: boolean }) {
  const t = useT()
  const { state } = useCaseState()
  const deadline = state.deadline
  if (!deadline) return null
  const lang = state.caseInfo.lang
  const date = formatDate(deadline.date, lang)
  // Reference date: the RFI date for the sample case (demo countdown), else the local date.
  const today = (isSample && state.caseInfo.rfiReceivedDate) || localTodayIso()
  const view: DeadlineView = state.rules
    ? deadlineView(today, deadline.date, state.rules.thresholds.rfiResponseDays)
    : { kind: 'dateOnly' }
  const passed = view.kind === 'passed'
  const tone = passed
    ? 'border-short bg-short-soft text-short'
    : 'border-brand bg-brand-soft text-brand-strong'
  return (
    <div
      role="status"
      className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[var(--radius-card)] border-2 px-3 py-2 font-semibold shadow-[var(--shadow-card)] ${tone}`}
    >
      <StatusIcon kind="calendar" className="h-5 w-5" />
      <span>{passed ? fill(t('replyPassed'), { date }) : fill(t('replyBy'), { date })}</span>
      {deadline.ruleStatus !== 'confirmed' && (
        <span className="rounded border border-current px-1.5 text-sm font-medium">
          {t(`ruleStatus_${deadline.ruleStatus}`)}
        </span>
      )}
      {!state.rules && <InlineSkeleton className="w-20" />}
      {view.kind === 'upcoming' && <span className="tabular font-bold">{fill(t('daysLeft'), { n: view.daysLeft })}</span>}
    </div>
  )
}
