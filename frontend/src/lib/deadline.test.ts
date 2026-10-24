import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { daysBetween, deadlineView } from './deadline'

// Add `days` calendar days to a "YYYY-MM-DD" date.
function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10)
}

describe('deadlineView', () => {
  it('classifies upcoming, dateOnly, and passed for a generated window', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 365 }), (windowDays) => {
        const today = '2027-06-12'
        expect(deadlineView(today, addDays(today, windowDays), windowDays)).toEqual({
          kind: 'upcoming',
          daysLeft: windowDays,
        })
        expect(deadlineView(today, today, windowDays)).toEqual({ kind: 'upcoming', daysLeft: 0 })
        expect(deadlineView(today, addDays(today, windowDays + 1), windowDays)).toEqual({ kind: 'dateOnly' })
        expect(deadlineView(today, addDays(today, -1), windowDays)).toEqual({ kind: 'passed' })
      }),
    )
  })

  it('counts calendar days across month and year ends', () => {
    expect(daysBetween('2026-12-31', '2027-01-01')).toBe(1)
    expect(daysBetween('2027-02-28', '2027-03-01')).toBe(1)
  })

  it('falls back to dateOnly for a malformed date', () => {
    expect(deadlineView('not-a-date', '2027-07-12', 1)).toEqual({ kind: 'dateOnly' })
  })
})
