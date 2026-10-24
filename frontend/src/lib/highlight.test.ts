import { describe, expect, it } from 'vitest'
import { findLine } from './highlight'

const lines = [
  { text: 'QuickDash Weekly Summary' },
  { text: 'Hours online:  12.50 hours' },
  { text: 'hours online: 12.50' },
  { text: 'Total earnings $310.00' },
]

describe('findLine', () => {
  it('prefers an exact normalized match over an earlier containing line', () => {
    expect(findLine(lines, '  HOURS online:   12.50 ')).toBe(2)
  })
  it('falls back to the first line that contains the evidence', () => {
    expect(findLine(lines, '$310.00')).toBe(3)
    expect(findLine(lines, 'hours online')).toBe(1)
  })
  it('returns null when nothing matches', () => {
    expect(findLine(lines, 'Harbor Cafe')).toBeNull()
    expect(findLine([], 'anything')).toBeNull()
  })
  it('returns null for empty or missing evidence', () => {
    expect(findLine(lines, '')).toBeNull()
    expect(findLine(lines, '   ')).toBeNull()
    expect(findLine(lines, null)).toBeNull()
    expect(findLine(lines, undefined)).toBeNull()
  })
})
