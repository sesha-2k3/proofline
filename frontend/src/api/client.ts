import createClient from 'openapi-fetch'
import type { paths } from './schema'

// Typed client generated from shared/openapi.json. All API calls go through this file.
export const api = createClient<paths>({ baseUrl: '' })

export class ApiError extends Error {
  code: string

  constructor(message: string, code: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
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

// Endpoint wrappers (health, rules, samples, documents, validate, evaluate,
// packet, timeline) are added once shared/openapi.json contains those paths.
// Pending B4: see docs/FRONTEND_REQUESTS.md.
