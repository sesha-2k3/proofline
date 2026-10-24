import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

// Typed client generated from shared/openapi.json. All API calls go through this file.
export const api = createClient<paths>({ baseUrl: '' })

type Schemas = components['schemas']
export type CaseInfo = Schemas['CaseInfo']
export type DocType = Schemas['DocumentResult']['docType']
export type DocumentResult = Schemas['DocumentResult']
export type EvidenceRecord = Schemas['EvidenceRecord']
export type ExemptionAnswer = Schemas['ExemptionAnswer']
export type EvaluateResponse = Schemas['EvaluateResponse']
export type HealthResponse = Schemas['HealthResponse']
export type RulesResponse = Schemas['RulesResponse']
export type SamplesResponse = Schemas['SamplesResponse']
export type SubmissionEntry = Schemas['SubmissionEntry']
export type ValidateRequest = Schemas['ValidateRequest']
export type EvaluateRequest = Schemas['EvaluateRequest']
export type PacketRequest = Schemas['PacketRequest']
export type TimelineRequest = Schemas['TimelineRequest']

export class ApiError extends Error {
  code: string
  constructor(message: string, code: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

// The backend sends errors as ErrorBody: {"error": {"code", "message", "details"}}.
// ErrorBody is not in the OpenAPI schema (see docs/FRONTEND_REQUESTS.md), so the
// error is read defensively from unknown JSON.
function toApiError(error: unknown, status: number): ApiError {
  if (typeof error === 'object' && error !== null && 'error' in error) {
    const detail = (error as { error: unknown }).error
    if (typeof detail === 'object' && detail !== null) {
      const { code, message } = detail as { code?: unknown; message?: unknown }
      if (typeof code === 'string' && typeof message === 'string') return new ApiError(message, code)
    }
  }
  if (status === 422) return new ApiError('The request was not valid.', 'BAD_REQUEST')
  return new ApiError(`Request failed (${status}).`, 'INTERNAL')
}

type Result<T> = { data?: T; error?: unknown; response: Response }

function unwrap<T>({ data, error, response }: Result<T>): T {
  if (error !== undefined || !response.ok || data === undefined) throw toApiError(error, response.status)
  return data
}

// Saves a PDF (or any blob) returned by /api/packet or /api/timeline.
export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function fileNameFrom(response: Response, fallback: string): string {
  const match = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')
  return match ? match[1] : fallback
}

export async function getHealth(): Promise<HealthResponse> {
  return unwrap(await api.GET('/api/health'))
}

export async function getRules(): Promise<RulesResponse> {
  return unwrap(await api.GET('/api/rules'))
}

export async function getSamples(): Promise<SamplesResponse> {
  return unwrap(await api.GET('/api/samples'))
}

export async function postDocument(file: File, docId: string, docTypeHint?: DocType): Promise<DocumentResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_id', docId)
  if (docTypeHint) form.append('doc_type_hint', docTypeHint)
  return unwrap(
    await api.POST('/api/documents', {
      // The generated multipart body types `file` as string; send the real FormData.
      body: { file: '', doc_id: docId },
      bodySerializer: () => form,
    }),
  )
}

export async function validateRecords(body: ValidateRequest): Promise<EvidenceRecord[]> {
  return unwrap(await api.POST('/api/validate', { body })).records
}

export async function evaluate(body: EvaluateRequest): Promise<EvaluateResponse> {
  return unwrap(await api.POST('/api/evaluate', { body }))
}

// Downloads the evidence packet PDF and returns the blob.
export async function downloadPacket(body: PacketRequest): Promise<Blob> {
  const result = await api.POST('/api/packet', { body, parseAs: 'blob' })
  const blob = unwrap(result as Result<Blob>)
  downloadBlob(blob, fileNameFrom(result.response, 'proofline-packet.pdf'))
  return blob
}

// Downloads the submission record PDF and returns the blob.
export async function downloadTimeline(body: TimelineRequest): Promise<Blob> {
  const result = await api.POST('/api/timeline', { body, parseAs: 'blob' })
  const blob = unwrap(result as Result<Blob>)
  downloadBlob(blob, fileNameFrom(result.response, 'proofline-submission-record.pdf'))
  return blob
}
