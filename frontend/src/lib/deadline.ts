// Pure helpers for the deadline chip (Requirement 3, design decision 2).
// The deadline date always comes from the API; only the display count is computed here.

export type DeadlineView = { kind: 'upcoming'; daysLeft: number } | { kind: 'dateOnly' } | { kind: 'passed' }

const DAY_MS = 24 * 60 * 60 * 1000

// "YYYY-MM-DD" -> UTC midnight in ms, or null when malformed.
function dayValue(iso: string): number | null {
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return null
  return Date.UTC(y, m - 1, d)
}

// Whole calendar days from `fromIso` to `toIso` (negative when `toIso` is earlier).
export function daysBetween(fromIso: string, toIso: string): number | null {
  const from = dayValue(fromIso)
  const to = dayValue(toIso)
  if (from === null || to === null) return null
  return Math.round((to - from) / DAY_MS)
}

// The local calendar date as "YYYY-MM-DD".
export function localTodayIso(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

// `windowDays` is rules.thresholds.rfiResponseDays.
export function deadlineView(todayIso: string, deadline: string, windowDays: number): DeadlineView {
  const days = daysBetween(todayIso, deadline)
  if (days === null) return { kind: 'dateOnly' }
  if (days < 0) return { kind: 'passed' }
  if (days <= windowDays) return { kind: 'upcoming', daysLeft: days }
  return { kind: 'dateOnly' }
}
