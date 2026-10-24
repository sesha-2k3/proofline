import { describe, expect, it } from 'vitest'
import type { DocumentResult } from '../api/client'
import type { CaseDocument, DocumentStatus } from '../state/caseState'
import { STAGE_ORDER, stageChips, type PipelineStage } from './stages'

function doc(
  status: DocumentStatus,
  pipeline: PipelineStage[] = [],
  warnings: string[] = [],
): CaseDocument {
  const result =
    status === 'done' ? ({ pipeline, warnings } as unknown as DocumentResult) : null
  return { docId: 'd1', file: {} as File, objectUrl: '', status, result }
}

const stage = (name: PipelineStage['stage'], status: PipelineStage['status']): PipelineStage => ({
  stage: name,
  status,
  durationMs: 1,
  detail: '',
})

describe('stageChips', () => {
  it('shows six working chips while queued or uploading', () => {
    for (const status of ['queued', 'uploading'] as const) {
      const { chips, openDetails } = stageChips(doc(status))
      expect(chips.map((c) => c.stage)).toEqual(STAGE_ORDER)
      expect(chips.every((c) => c.status === 'working')).toBe(true)
      expect(openDetails).toBe(false)
    }
  })

  it('marks every chip failed on error', () => {
    const { chips } = stageChips(doc('error'))
    expect(chips).toHaveLength(6)
    expect(chips.every((c) => c.status === 'failed')).toBe(true)
  })

  it('maps pipeline statuses in fixed order and fills missing stages with skipped', () => {
    const pipeline = [stage('verify', 'ok'), stage('ingest', 'ok'), stage('extract', 'ok')]
    const { chips, openDetails } = stageChips(doc('done', pipeline))
    expect(chips).toEqual([
      { stage: 'ingest', status: 'ok' },
      { stage: 'render', status: 'skipped' },
      { stage: 'classify', status: 'skipped' },
      { stage: 'extract', status: 'ok' },
      { stage: 'normalize', status: 'skipped' },
      { stage: 'verify', status: 'ok' },
    ])
    expect(openDetails).toBe(false)
  })

  it('opens details on a warning stage or result warnings', () => {
    const all = STAGE_ORDER.map((s) => stage(s, 'ok'))
    const warned = all.map((s) => (s.stage === 'verify' ? stage('verify', 'warning') : s))
    expect(stageChips(doc('done', warned)).openDetails).toBe(true)
    expect(stageChips(doc('done', all, ['Low confidence'])).openDetails).toBe(true)
    expect(stageChips(doc('done', all)).openDetails).toBe(false)
  })
})
