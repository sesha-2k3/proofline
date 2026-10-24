import { useState, type FormEvent } from 'react'
import { downloadPacket, downloadTimeline, type SubmissionEntry } from '../api/client'
import { formatDate } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { firstName } from '../lib/story'
import { useCaseState } from '../state/caseState'

type Channel = SubmissionEntry['channel']
const CHANNELS: Channel[] = ['online', 'mail', 'fax', 'in_person', 'phone']

// Today's date in the browser's time zone, as YYYY-MM-DD.
function today(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const inputClass = 'w-full rounded-md border border-line bg-surface px-3 py-2'
const primaryButton =
  'rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong disabled:opacity-50'
const secondaryButton =
  'rounded-md border border-brand bg-surface px-5 py-3 font-semibold text-brand-strong hover:bg-brand-soft disabled:opacity-50'

// Step 5 (F7): download the evidence packet, log submissions, download the submission record.
export function PacketPanel({ onBack }: { onBack: () => void }) {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const { caseInfo, evaluation, records, submissions } = state
  const lang = caseInfo.lang
  const name = firstName(caseInfo.clientName)
  const documentNames = state.documents.filter((d) => d.status === 'done').map((d) => d.file.name)

  const [busy, setBusy] = useState<'packet' | 'record' | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [submittedAt, setSubmittedAt] = useState(today())
  const [channel, setChannel] = useState<Channel>('online')
  const [confirmationNumber, setConfirmationNumber] = useState('')
  const [included, setIncluded] = useState<string[]>(documentNames)
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  async function getPacket() {
    if (!evaluation) return
    setBusy('packet')
    setError(null)
    setStatus(t('packetPreparing'))
    try {
      await downloadPacket({ caseInfo, records, evaluation })
      setStatus(t('packetDownloaded'))
    } catch {
      setStatus('')
      setError(t('packetError'))
    } finally {
      setBusy(null)
    }
  }

  async function getRecord() {
    setBusy('record')
    setError(null)
    setStatus(t('recordPreparing'))
    try {
      await downloadTimeline({ caseInfo, submissions })
      setStatus(t('recordReady'))
    } catch {
      setStatus('')
      setError(t('recordError'))
    } finally {
      setBusy(null)
    }
  }

  function addSubmission(event: FormEvent) {
    event.preventDefault()
    if (!/^\d{4}-\d{2}-\d{2}$/.test(submittedAt)) {
      setFormError(t('errorSubmittedAt'))
      return
    }
    setFormError(null)
    dispatch({
      type: 'ADD_SUBMISSION',
      submission: {
        submittedAt,
        channel,
        confirmationNumber: confirmationNumber.trim() || null,
        documentsIncluded: included,
        notes: notes.trim() || null,
      },
    })
    setConfirmationNumber('')
    setNotes('')
    setStatus(t('submissionAdded'))
  }

  function toggleIncluded(name: string, checked: boolean) {
    setIncluded((prev) => (checked ? [...prev.filter((n) => n !== name), name] : prev.filter((n) => n !== name)))
  }

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold text-ink">{t('packetTitle')}</h2>

      <p aria-live="polite" className="sr-only">
        {status}
      </p>
      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-md border border-short bg-short-soft p-3">
          <p className="flex-1 text-short">{error}</p>
          <button type="button" onClick={() => setError(null)} className="text-sm font-semibold underline">
            {t('dismiss')}
          </button>
        </div>
      )}

      <div
        className={
          evaluation
            ? 'space-y-4 rounded-[var(--radius-card)] border-2 border-brand bg-brand-soft shadow-[var(--shadow-card)] p-5'
            : 'space-y-3 rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4'
        }
      >
        {evaluation ? (
          <h3 className="text-2xl font-bold text-ink">{fill(t('packetReady'), { name })}</h3>
        ) : (
          <h3 className="text-lg font-semibold">{t('packetHeading')}</h3>
        )}
        <p className="text-muted">{t('packetIntro')}</p>
        <p className="rounded-md bg-surface p-3 text-sm">{t('packetDisclaimer')}</p>
        <p className="font-medium text-ink">{t('closeLine')}</p>
        <p className="text-ink">{fill(t('youSend'), { name })}</p>
        {!evaluation && <p className="text-conditional">{t('packetNeedsEvaluation')}</p>}
        <button
          type="button"
          disabled={!evaluation || busy !== null}
          onClick={() => void getPacket()}
          className={`${primaryButton} w-full text-lg sm:w-auto`}
        >
          {busy === 'packet' ? t('packetPreparing') : t('downloadPacket')}
        </button>
      </div>

      <form onSubmit={addSubmission} noValidate className="space-y-4 rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4">
        <h3 className="text-lg font-semibold">{t('submissionLogTitle')}</h3>
        <p className="text-muted">{t('submissionLogIntro')}</p>

        {formError && (
          <p role="alert" className="rounded-md border border-short bg-short-soft p-3 text-short">
            {formError}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="submittedAt" className="mb-1 block font-medium">
              {t('submittedAt')}
            </label>
            <input
              id="submittedAt"
              type="date"
              required
              value={submittedAt}
              onChange={(e) => setSubmittedAt(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="channel" className="mb-1 block font-medium">
              {t('channel')}
            </label>
            <select id="channel" value={channel} onChange={(e) => setChannel(e.target.value as Channel)} className={inputClass}>
              {CHANNELS.map((c) => (
                <option key={c} value={c}>
                  {t(`channel_${c}`)}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="confirmationNumber" className="mb-1 block font-medium">
              {t('confirmationNumber')}
            </label>
            <input
              id="confirmationNumber"
              type="text"
              value={confirmationNumber}
              onChange={(e) => setConfirmationNumber(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        <fieldset>
          <legend className="mb-1 font-medium">{t('documentsIncluded')}</legend>
          {documentNames.length === 0 ? (
            <p className="text-muted">{t('noDocuments')}</p>
          ) : (
            <ul className="space-y-1">
              {documentNames.map((name) => (
                <li key={name}>
                  <label className="flex items-center gap-2 break-all">
                    <input
                      type="checkbox"
                      checked={included.includes(name)}
                      onChange={(e) => toggleIncluded(name, e.target.checked)}
                      className="h-4 w-4"
                    />
                    {name}
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        <div>
          <label htmlFor="notes" className="mb-1 block font-medium">
            {t('notes')}
          </label>
          <textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} className={inputClass} />
        </div>

        <button type="submit" className={secondaryButton}>
          {t('addSubmission')}
        </button>
      </form>

      <div className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4">
        <h3 className="text-lg font-semibold">{t('submissionsTitle')}</h3>
        {submissions.length === 0 ? (
          <p className="text-muted">{t('noSubmissions')}</p>
        ) : (
          <ul className="space-y-3">
            {submissions.map((s, i) => (
              <li key={`${s.submittedAt}-${i}`} className="flex flex-wrap items-start gap-3 border-b border-line pb-3">
                <div className="flex-1 space-y-0.5">
                  <p className="font-medium">
                    {formatDate(s.submittedAt, lang)} · {t(`channel_${s.channel}`)}
                  </p>
                  {s.confirmationNumber && (
                    <p className="text-sm">{fill(t('confirmationLine'), { number: s.confirmationNumber })}</p>
                  )}
                  <p className="text-sm break-all text-muted">
                    {fill(t('documentsLine'), { docs: s.documentsIncluded.length > 0 ? s.documentsIncluded.join(', ') : '—' })}
                  </p>
                  {s.notes && <p className="text-sm text-muted">{s.notes}</p>}
                </div>
                <button
                  type="button"
                  onClick={() => dispatch({ type: 'REMOVE_SUBMISSION', index: i })}
                  className="text-sm font-semibold text-short underline"
                  aria-label={fill(t('removeSubmission'), { date: formatDate(s.submittedAt, lang) })}
                >
                  {t('removeDocument')}
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          disabled={submissions.length === 0 || busy !== null}
          onClick={() => void getRecord()}
          className={primaryButton}
        >
          {busy === 'record' ? t('recordPreparing') : t('downloadRecord')}
        </button>
      </div>

      <button type="button" onClick={onBack} className={secondaryButton}>
        {t('backToResults')}
      </button>
    </section>
  )
}
