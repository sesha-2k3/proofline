import type { EvaluateResponse, EvidenceRecord, MonthStatus } from '../api/client'

// Pure helpers for the Jorge story UI. No side effects.

// First whitespace-separated token of the name, or the full trimmed name.
export function firstName(clientName: string): string {
  const trimmed = clientName.trim()
  return trimmed.split(/\s+/)[0] ?? trimmed
}

// Distinct issuers (trimmed, case-folded for comparison) in first-seen order.
// Returns the trimmed display value of the first occurrence.
export function caseSources(records: readonly EvidenceRecord[]): string[] {
  const seen = new Set<string>()
  const sources: string[] = []
  for (const record of records) {
    const display = (record.issuer.value ?? '').trim()
    if (!display) continue
    const key = display.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    sources.push(display)
  }
  return sources
}

export type StoryHeadline =
  | { kind: 'meets'; month: string; hours: number; sources: number }
  | { kind: 'conditional'; month: string; ruleIds: string[] }
  | { kind: 'none' }

// Headline facts for the best month, computed from the evaluation and records.
export function storyHeadline(
  evaluation: EvaluateResponse,
  records: readonly EvidenceRecord[],
): StoryHeadline {
  const best = evaluation.bestMonth
    ? evaluation.months.find((m) => m.month === evaluation.bestMonth)
    : undefined
  if (!best) return { kind: 'none' }
  if (best.status === 'conditional') {
    return { kind: 'conditional', month: best.month, ruleIds: [...best.dependsOnUnresolved] }
  }
  if (best.status !== 'meets') return { kind: 'none' }
  // Work + volunteer only, matching the ledger's meets path. Training hours
  // count only toward a conditional outcome (job_training_approved unresolved).
  const hours = (Math.round(best.workHours * 100) + Math.round(best.volunteerHours * 100)) / 100
  const counted = new Set(best.countedRecordIds)
  const issuers = new Set<string>()
  for (const record of records) {
    if (!counted.has(record.id)) continue
    const key = (record.issuer.value ?? '').trim().toLowerCase()
    if (key) issuers.add(key)
  }
  return { kind: 'meets', month: best.month, hours, sources: issuers.size }
}

// Fill fraction for a month's progress bar, clamped to [0, 1].
export function progressFraction(countedHours: number, thresholdHours: number): number {
  if (!(thresholdHours > 0)) return 0
  return Math.min(1, Math.max(0, countedHours / thresholdHours))
}

export interface StatusChange {
  month: string
  from: MonthStatus
  to: MonthStatus
  animate: boolean
}

// Months present in both evaluations whose status differs, in `next` month order.
export function statusChanges(
  prior: EvaluateResponse | null,
  next: EvaluateResponse,
): StatusChange[] {
  if (!prior) return []
  const before = new Map(prior.months.map((m) => [m.month, m.status]))
  const changes: StatusChange[] = []
  for (const m of next.months) {
    const from = before.get(m.month)
    if (from === undefined || from === m.status) continue
    changes.push({
      month: m.month,
      from,
      to: m.status,
      animate: from === 'conditional' && m.status === 'meets',
    })
  }
  return changes
}
