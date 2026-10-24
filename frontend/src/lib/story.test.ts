import { describe, expect, it } from 'vitest'
import type { EvaluateResponse, EvidenceRecord, MonthResult } from '../api/client'
import { caseSources, firstName, progressFraction, statusChanges, storyHeadline } from './story'

function withIssuer(value: string | null): EvidenceRecord {
  return { issuer: { value, confidence: 'high' } } as unknown as EvidenceRecord
}

describe('firstName', () => {
  it('returns the first token', () => {
    expect(firstName('Jorge Ramos')).toBe('Jorge')
    expect(firstName('  Jorge   Ramos ')).toBe('Jorge')
  })
  it('returns the trimmed name when there is one token', () => {
    expect(firstName(' Jorge ')).toBe('Jorge')
    expect(firstName('')).toBe('')
  })
})

describe('caseSources', () => {
  it('dedupes trimmed, case-folded issuers in first-seen order', () => {
    const records = [
      withIssuer('QuickDash'),
      withIssuer(' quickdash '),
      withIssuer('Harbor Cafe'),
      withIssuer(null),
      withIssuer('HARBOR CAFE'),
      withIssuer('Ramos Family Bakery'),
    ]
    expect(caseSources(records)).toEqual(['QuickDash', 'Harbor Cafe', 'Ramos Family Bakery'])
  })
})

function month(m: string, status: MonthResult['status'], extra: Partial<MonthResult> = {}): MonthResult {
  return {
    month: m,
    workHours: 0,
    volunteerHours: 0,
    trainingHours: 0,
    schoolHalfTime: false,
    grossIncomeCents: 0,
    netIncomeCents: 0,
    status,
    pathsMet: [],
    dependsOnUnresolved: [],
    hoursShortfall: 0,
    incomeShortfallCents: 0,
    countedRecordIds: [],
    excludedRecordIds: [],
    ...extra,
  }
}

function evaluation(months: MonthResult[], bestMonth: string | null = null): EvaluateResponse {
  return {
    months,
    bestMonth,
    possibleExemptions: [],
    gaps: [],
    summary: '',
    demoMode: true,
    rulesVersion: 'test',
  }
}

function rec(id: string, issuer: string | null): EvidenceRecord {
  return { id, issuer: { value: issuer, confidence: 'high' } } as unknown as EvidenceRecord
}

describe('storyHeadline', () => {
  it('meets: sums hours in hundredths and counts distinct counted issuers', () => {
    const ev = evaluation(
      [
        month('2026-04', 'short'),
        month('2026-05', 'meets', {
          workHours: 0.1,
          volunteerHours: 0.2,
          countedRecordIds: ['a', 'b', 'c'],
        }),
      ],
      '2026-05',
    )
    const records = [rec('a', 'QuickDash'), rec('b', ' quickdash '), rec('c', 'Harbor Cafe'), rec('d', 'Ramos Family Bakery')]
    expect(storyHeadline(ev, records)).toEqual({ kind: 'meets', month: '2026-05', hours: 0.3, sources: 2 })
  })

  it('conditional: names the unresolved rules', () => {
    const ev = evaluation([month('2026-05', 'conditional', { dependsOnUnresolved: ['rule_x'] })], '2026-05')
    expect(storyHeadline(ev, [])).toEqual({ kind: 'conditional', month: '2026-05', ruleIds: ['rule_x'] })
  })

  it('none when there is no best month or it is short', () => {
    expect(storyHeadline(evaluation([month('2026-05', 'short')]), [])).toEqual({ kind: 'none' })
    expect(storyHeadline(evaluation([month('2026-05', 'short')], '2026-05'), [])).toEqual({ kind: 'none' })
  })
})

describe('progressFraction', () => {
  it('divides and clamps to [0, 1]', () => {
    expect(progressFraction(7, 14)).toBe(0.5)
    expect(progressFraction(13, 7)).toBe(1)
    expect(progressFraction(-1, 7)).toBe(0)
  })
  it('is 0 when the threshold is not positive', () => {
    expect(progressFraction(7, 0)).toBe(0)
    expect(progressFraction(7, -13)).toBe(0)
  })
})

describe('statusChanges', () => {
  it('returns [] when prior is null', () => {
    expect(statusChanges(null, evaluation([month('2026-05', 'meets')]))).toEqual([])
  })
  it('lists months in both with a different status; animates only conditional to meets', () => {
    const prior = evaluation([month('2026-04', 'conditional'), month('2026-05', 'meets'), month('2026-06', 'short')])
    const next = evaluation([month('2026-04', 'meets'), month('2026-05', 'conditional'), month('2026-06', 'short'), month('2026-07', 'meets')])
    expect(statusChanges(prior, next)).toEqual([
      { month: '2026-04', from: 'conditional', to: 'meets', animate: true },
      { month: '2026-05', from: 'meets', to: 'conditional', animate: false },
    ])
  })
})
