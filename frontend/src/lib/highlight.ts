function normalize(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase()
}

/**
 * Index of the line that best matches the evidence text.
 * First exact match after normalization (collapse whitespace, trim, case-fold),
 * else the first line containing the evidence, else null.
 */
export function findLine(
  lines: readonly { text: string }[],
  evidence: string | null | undefined,
): number | null {
  if (evidence == null) return null
  const target = normalize(evidence)
  if (target === '') return null
  const normalized = lines.map((line) => normalize(line.text))
  const exact = normalized.indexOf(target)
  if (exact !== -1) return exact
  const partial = normalized.findIndex((text) => text.includes(target))
  return partial === -1 ? null : partial
}
