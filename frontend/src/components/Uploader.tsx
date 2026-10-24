import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { ApiError, postDocument, validateRecords, type DocType, type SamplesResponse } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { fill, useT } from '../i18n/useT'
import { useCaseState, type CaseDocument } from '../state/caseState'
import { PipelineTrace } from './PipelineTrace'
import { StageStrip } from './StageStrip'

// Upload limit shown to the user and checked before sending. The backend enforces
// MAX_UPLOAD_MB (default 10) and answers UNSUPPORTED_FILE either way.
const MAX_UPLOAD_MB = 10
const ACCEPT = '.pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg'
const ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg']

// Choices for an "unknown" document. Record<> keeps this in sync with the generated DocType.
const DOC_TYPE_LABELS: Record<Exclude<DocType, 'unknown'>, MessageKey> = {
  rfi_notice: 'docType_rfi_notice',
  paystub: 'docType_paystub',
  employer_statement: 'docType_employer_statement',
  gig_earnings: 'docType_gig_earnings',
  volunteer_letter: 'docType_volunteer_letter',
  school_letter: 'docType_school_letter',
}
const DOC_TYPE_CHOICES = Object.keys(DOC_TYPE_LABELS) as Exclude<DocType, 'unknown'>[]

const STATUS_LABEL: Record<CaseDocument['status'], MessageKey> = {
  queued: 'statusQueued',
  uploading: 'statusUploading',
  done: 'statusDone',
  error: 'statusError',
}

function isAllowed(file: File): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  return ALLOWED_EXTENSIONS.includes(ext) && file.size <= MAX_UPLOAD_MB * 1024 * 1024
}

function typeFromName(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return 'application/pdf'
  if (ext === 'png') return 'image/png'
  if (ext === 'jpg' || ext === 'jpeg') return 'image/jpeg'
  return ''
}

interface UploaderProps {
  samples: SamplesResponse | null
  onContinue: () => void
  onBack: () => void
}

export function Uploader({ samples, onContinue, onBack }: UploaderProps) {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const [dragging, setDragging] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [validating, setValidating] = useState(false)
  const [hints, setHints] = useState<Record<string, Exclude<DocType, 'unknown'>>>({})
  const inputRef = useRef<HTMLInputElement>(null)
  const samplesStarted = useRef(false)

  const errorText = useCallback(
    (error: unknown) =>
      error instanceof ApiError && error.code === 'UNSUPPORTED_FILE'
        ? fill(t('errorUnsupportedFile'), { mb: MAX_UPLOAD_MB })
        : t('errorUploadFailed'),
    [t],
  )

  // Screen-reader announcement for upload start/finish/failure (aria-live polite region).
  const [announcement, setAnnouncement] = useState('')
  const announce = useCallback(
    (key: 'uploadAnnounceStart' | 'uploadAnnounceDone' | 'uploadAnnounceError', file: File) =>
      setAnnouncement(fill(t(key), { file: file.name })),
    [t],
  )

  const upload = useCallback(
    async (docId: string, file: File, docTypeHint?: DocType) => {
      dispatch({ type: 'UPDATE_DOCUMENT', docId, changes: { status: 'uploading', error: undefined } })
      announce('uploadAnnounceStart', file)
      try {
        const result = await postDocument(file, docId, docTypeHint)
        dispatch({ type: 'UPDATE_DOCUMENT', docId, changes: { status: 'done', result } })
        announce('uploadAnnounceDone', file)
      } catch (error) {
        dispatch({ type: 'UPDATE_DOCUMENT', docId, changes: { status: 'error', result: null, error: errorText(error) } })
        announce('uploadAnnounceError', file)
      }
    },
    [dispatch, errorText, announce],
  )

  // Adds files to the case and uploads them in parallel. Files that fail the
  // type/size check are listed with an error and are not sent.
  const addFiles = useCallback(
    async (files: File[]) => {
      const uploads: Promise<void>[] = []
      for (const file of files) {
        const docId = crypto.randomUUID()
        const allowed = isAllowed(file)
        dispatch({
          type: 'ADD_DOCUMENT',
          document: {
            docId,
            file,
            objectUrl: URL.createObjectURL(file),
            status: allowed ? 'queued' : 'error',
            result: null,
            error: allowed ? undefined : fill(t('errorUnsupportedFile'), { mb: MAX_UPLOAD_MB }),
          },
        })
        if (allowed) uploads.push(upload(docId, file))
        else announce('uploadAnnounceError', file)
      }
      await Promise.all(uploads)
    },
    [dispatch, t, upload, announce],
  )

  // Sample mode: fetch each /samples/<name> as a File and upload it (once per case).
  useEffect(() => {
    if (!samples || samplesStarted.current || state.documents.length > 0) return
    samplesStarted.current = true
    setNotice(t('sampleUploading'))
    Promise.all(
      samples.files.map(async (sample) => {
        try {
          const response = await fetch(sample.url)
          if (!response.ok) throw new Error(String(response.status))
          const blob = await response.blob()
          return new File([blob], sample.name, { type: blob.type || typeFromName(sample.name) })
        } catch {
          setNotice(fill(t('sampleFetchError'), { name: sample.name }))
          return null
        }
      }),
    ).then((files) => {
      setNotice((current) => (current === t('sampleUploading') ? null : current))
      return addFiles(files.filter((f): f is File => f !== null))
    })
  }, [samples, state.documents.length, addFiles, t])

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    void addFiles(Array.from(event.dataTransfer.files))
  }

  const remove = (doc: CaseDocument) => {
    URL.revokeObjectURL(doc.objectUrl)
    dispatch({ type: 'REMOVE_DOCUMENT', docId: doc.docId })
  }

  const docs = state.documents
  const doneCount = docs.filter((d) => d.status === 'done').length
  const busy = docs.some((d) => d.status === 'queued' || d.status === 'uploading')
  const canContinue = doneCount > 0 && !busy && !validating

  const continueToReview = async () => {
    setValidating(true)
    setNotice(null)
    try {
      const records = docs.flatMap((d) => d.result?.records ?? [])
      const validated = await validateRecords({ caseInfo: state.caseInfo, records })
      dispatch({ type: 'SET_RECORDS', records: validated })
      onContinue()
    } catch {
      setNotice(t('validateError'))
    } finally {
      setValidating(false)
    }
  }

  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold text-ink">{t('documentsTitle')}</h2>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-[var(--radius-card)] border-2 border-dashed p-6 text-center ${
          dragging ? 'border-brand bg-brand-soft' : 'border-line bg-surface'
        }`}
      >
        <p>
          {t('dropHere')}{' '}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="rounded-md bg-brand px-3 py-1.5 font-semibold text-white hover:bg-brand-strong"
          >
            {t('chooseFiles')}
          </button>
        </p>
        <p className="mt-2 text-sm text-muted">{fill(t('fileTypesHelp'), { mb: MAX_UPLOAD_MB })}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(e) => {
            void addFiles(Array.from(e.target.files ?? []))
            e.target.value = ''
          }}
        />
      </div>

      {notice && (
        <div role="alert" className="flex items-start gap-3 rounded-md border border-conditional bg-conditional-soft p-3">
          <p className="flex-1 text-conditional">{notice}</p>
          <button type="button" onClick={() => setNotice(null)} className="text-sm font-semibold underline">
            {t('dismiss')}
          </button>
        </div>
      )}

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <p className="text-sm text-muted">
        {docs.length === 0 ? t('noDocuments') : fill(t('uploadStatusSummary'), { done: doneCount, total: docs.length })}
      </p>

      <ul className="space-y-3">
        {docs.map((doc) => {
          const result = doc.result
          const unknown = result?.docType === 'unknown'
          const hint = hints[doc.docId] ?? ''
          return (
            <li key={doc.docId} className="rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-medium break-all">{doc.file.name}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-sm ${
                    doc.status === 'error'
                      ? 'bg-short-soft text-short'
                      : doc.status === 'done'
                        ? 'bg-meets-soft text-meets'
                        : 'bg-brand-soft text-brand-strong'
                  }`}
                >
                  {t(STATUS_LABEL[doc.status])}
                </span>
                {result && <span className="text-sm text-muted">{t(`docType_${result.docType}`)}</span>}
                {result && result.records.length > 0 && (
                  <span className="text-sm text-muted">{fill(t('recordsFound'), { n: result.records.length })}</span>
                )}
                {result?.notice && <span className="text-sm text-muted">{t('noticeFound')}</span>}
                <span className="ml-auto flex gap-2">
                  {doc.status === 'error' && isAllowed(doc.file) && (
                    <button
                      type="button"
                      onClick={() => void upload(doc.docId, doc.file)}
                      className="text-sm font-semibold text-brand-strong underline"
                    >
                      {t('retryUpload')}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => remove(doc)}
                    disabled={doc.status === 'uploading'}
                    className="text-sm font-semibold text-short underline disabled:opacity-50"
                  >
                    {t('removeDocument')}
                  </button>
                </span>
              </div>

              <StageStrip document={doc} />

              {unknown && doc.status === 'done' && (
                <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md bg-conditional-soft p-3">
                  <p className="basis-full text-sm text-conditional">{t('unknownTypeHelp')}</p>
                  <label className="text-sm">
                    <span className="font-medium">{t('documentType')}</span>
                    <select
                      value={hint}
                      onChange={(e) =>
                        setHints((h) => ({ ...h, [doc.docId]: e.target.value as Exclude<DocType, 'unknown'> }))
                      }
                      className="mt-1 block rounded-md border border-line bg-surface px-2 py-1.5"
                    >
                      <option value="">{t('chooseType')}</option>
                      {DOC_TYPE_CHOICES.map((type) => (
                        <option key={type} value={type}>
                          {t(DOC_TYPE_LABELS[type])}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    disabled={!hint}
                    onClick={() => hint && void upload(doc.docId, doc.file, hint)}
                    className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
                  >
                    {t('uploadAgain')}
                  </button>
                </div>
              )}

              <PipelineTrace document={doc} />
            </li>
          )
        })}
      </ul>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md border border-brand bg-surface px-5 py-3 font-semibold text-brand-strong hover:bg-brand-soft"
        >
          {t('back')}
        </button>
        <button
          type="button"
          disabled={!canContinue}
          onClick={() => void continueToReview()}
          className="rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
        >
          {validating ? t('validating') : t('continueToReview')}
        </button>
      </div>
    </section>
  )
}
