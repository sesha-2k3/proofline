import type { DocumentResult } from '../api/client'
import type { CaseDocument } from '../state/caseState'

export type PipelineStage = DocumentResult['pipeline'][number]
export type StageName = PipelineStage['stage']
export type StageChipStatus = PipelineStage['status'] | 'working'

export interface StageChip {
  stage: StageName
  status: StageChipStatus
}

export const STAGE_ORDER: readonly StageName[] = [
  'ingest',
  'render',
  'classify',
  'extract',
  'normalize',
  'verify',
]

// Six chips in fixed order for one uploaded document, plus whether the
// detail view should open by default (any warning/failed stage or warning).
export function stageChips(document: CaseDocument): { chips: StageChip[]; openDetails: boolean } {
  if (document.status === 'queued' || document.status === 'uploading') {
    return { chips: STAGE_ORDER.map((stage) => ({ stage, status: 'working' })), openDetails: false }
  }
  if (document.status === 'error') {
    return { chips: STAGE_ORDER.map((stage) => ({ stage, status: 'failed' })), openDetails: true }
  }
  const pipeline = document.result?.pipeline ?? []
  const chips: StageChip[] = STAGE_ORDER.map((stage) => ({
    stage,
    status: pipeline.find((entry) => entry.stage === stage)?.status ?? 'skipped',
  }))
  const openDetails =
    pipeline.some((entry) => entry.status === 'warning' || entry.status === 'failed') ||
    (document.result?.warnings.length ?? 0) > 0
  return { chips, openDetails }
}
