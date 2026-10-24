import { useRef, useState } from 'react'
import { FileSearch } from 'lucide-react'
import { evaluate, validateRecords, type EvidenceRecord, type PageView } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { fill, useT } from '../i18n/useT'
import { useCaseState, type CaseDocument } from '../state/caseState'
import { ExemptionQuestions } from './ExemptionQuestions'
import { SourceView } from './SourceView'
import { StatusIcon } from './StatusIcon'

type FieldKey =
  | 'personName'
  | 'issuer'
  | 'orgType'
  | 'nonPartisan'
  | 'periodStart'
  | 'periodEnd'
  | 'hours'
  | 'hourlyRateCents'
  | 'grossCents'
  | 'expensesCents'
  | 'halfTimeEnrolled'
  | 'documentDate'
type AnyField = NonNullable<EvidenceRecord[FieldKey]>
type FieldValue = AnyField['value']
type FieldKind = 'text' | 'date' | 'hours' | 'money' | 'bool' | 'orgType'

const FIELD_KIND: Record<FieldKey, FieldKind> = {
  personName: 'text',
  issuer: 'text',
  orgType: 'orgType',
  nonPartisan: 'bool',
  periodStart: 'date',
  periodEnd: 'date',
  hours: 'hours',
  hourlyRateCents: 'money',
  grossCents: 'money',
  expensesCents: 'money',
  halfTimeEnrolled: 'bool',
  documentDate: 'date',
}
const FIELD_ORDER = Object.keys(FIELD_KIND) as FieldKey[]
const ORG_TYPES = ['public', 'nonprofit', 'for_profit', 'political', 'unknown'] as const

const VERIFICATION_STYLE: Record<AnyField['verification'], string> = {
  grounded: 'bg-meets-soft text-meets',
  ungrounded: 'bg-short-soft text-short',
  not_checked: 'bg-canvas text-muted',
}

function needsConfirmation(field: AnyField): boolean {
  return !field.confirmed && (field.confidence === 'low' || field.verification === 'ungrounded')
}

// Counts the low-confidence fields the navigator has not confirmed yet.
function countUnconfirmed(records: EvidenceRecord[]): number {
  return records.reduce(
    (n, r) => n + FIELD_ORDER.filter((k) => r[k] && r[k].confidence === 'low' && !r[k].confirmed).length,
    0,
  )
}

function toDraft(kind: FieldKind, value: FieldValue): string {
  if (value === null) return ''
  if (kind === 'money' && typeof value === 'number') return (value / 100).toFixed(2)
  if (kind === 'hours' && typeof value === 'number') return value.toFixed(2)
  return String(value)
}

// Returns undefined when the draft is not a valid value.
function parseDraft(kind: FieldKind, draft: string): FieldValue | undefined {
  const text = draft.trim()
  if (text === '') return null
  if (kind === 'money' || kind === 'hours') {
    const n = Number(text.replace(/[$,]/g, ''))
    if (!Number.isFinite(n) || n < 0) return undefined
    return kind === 'money' ? Math.round(n * 100) : Math.round(n * 100) / 100
  }
  if (kind === 'bool') return text === 'true'
  if (kind === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(text)) return undefined
  return text as FieldValue
}

interface EditorProps {
  kind: FieldKind
  value: FieldValue
  label: string
  onCommit: (value: FieldValue) => void
}

function FieldEditor({ kind, value, label, onCommit }: EditorProps) {
  const t = useT()
  const [draft, setDraft] = useState(toDraft(kind, value))
  const [invalid, setInvalid] = useState(false)
  const base = 'w-full min-w-28 rounded-md border bg-surface px-2 py-1'

  if (kind === 'bool' || kind === 'orgType') {
    return (
      <select
        aria-label={label}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          const parsed = parseDraft(kind, e.target.value)
          if (parsed !== undefined) onCommit(parsed)
        }}
        className={`${base} border-line`}
      >
        <option value="">{t('notRead')}</option>
        {kind === 'bool' ? (
          <>
            <option value="true">{t('yes')}</option>
            <option value="false">{t('no')}</option>
          </>
        ) : (
          ORG_TYPES.map((o) => (
            <option key={o} value={o}>
              {t(`orgType_${o}`)}
            </option>
          ))
        )}
      </select>
    )
  }

  const commit = () => {
    if (draft === toDraft(kind, value)) return setInvalid(false)
    const parsed = parseDraft(kind, draft)
    if (parsed === undefined) return setInvalid(true)
    setInvalid(false)
    onCommit(parsed)
  }

  return (
    <>
      <input
        aria-label={label}
        aria-invalid={invalid}
        type={kind === 'date' ? 'date' : 'text'}
        inputMode={kind === 'money' || kind === 'hours' ? 'decimal' : undefined}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
        className={`${base} ${invalid ? 'border-short' : 'border-line'}`}
      />
      {invalid && <span className="block text-xs text-short">{t('invalidValue')}</span>}
    </>
  )
}

function Preview({ doc }: { doc: CaseDocument }) {
  const t = useT()
  const title = fill(t('documentPreview'), { name: doc.file.name })
  const isPdf = doc.file.type === 'application/pdf' || doc.file.name.toLowerCase().endsWith('.pdf')
  return (
    <div className="space-y-1">
      {isPdf ? (
        <object data={doc.objectUrl} type="application/pdf" title={title} className="h-96 w-full rounded-md border border-line lg:h-[32rem]">
          <a href={doc.objectUrl} target="_blank" rel="noreferrer" className="text-brand-strong underline">
            {t('openDocument')}
          </a>
        </object>
      ) : (
        <img src={doc.objectUrl} alt={title} className="max-h-[32rem] w-full rounded-md border border-line object-contain" />
      )}
      <a href={doc.objectUrl} target="_blank" rel="noreferrer" className="text-sm text-brand-strong underline">
        {t('openDocument')}
      </a>
    </div>
  )
}

interface ReviewPanelProps {
  onBack: () => void
  onEvaluated: () => void
}

export function ReviewPanel({ onBack, onEvaluated }: ReviewPanelProps) {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const [checking, setChecking] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestSeq = useRef(0)

  const records = state.records
  const unconfirmed = countUnconfirmed(records)

  // Applies a field change locally, then re-validates all records. Only the
  // newest validation response is kept.
  const changeField = (recordId: string, key: FieldKey, changes: Partial<AnyField>) => {
    const next = records.map((r) => {
      const field = r[key]
      return r.id === recordId && field ? ({ ...r, [key]: { ...field, ...changes } } as EvidenceRecord) : r
    })
    dispatch({ type: 'SET_RECORDS', records: next })
    dispatch({ type: 'SET_EVALUATION', evaluation: null })
    const seq = ++requestSeq.current
    setChecking(true)
    setError(null)
    validateRecords({ caseInfo: state.caseInfo, records: next })
      .then((validated) => seq === requestSeq.current && dispatch({ type: 'SET_RECORDS', records: validated }))
      .catch(() => seq === requestSeq.current && setError(t('revalidateError')))
      .finally(() => seq === requestSeq.current && setChecking(false))
  }

  const runEvaluate = async () => {
    setEvaluating(true)
    setError(null)
    try {
      const evaluation = await evaluate({
        caseInfo: state.caseInfo,
        records,
        exemptionAnswers: state.exemptionAnswers,
      })
      dispatch({ type: 'SET_EVALUATION', evaluation })
      onEvaluated()
    } catch {
      setError(t('evaluateError'))
    } finally {
      setEvaluating(false)
    }
  }

  // Group records by document, in upload order.
  const docIds = [...new Set([...state.documents.map((d) => d.docId), ...records.map((r) => r.docId)])].filter((id) =>
    records.some((r) => r.docId === id),
  )

  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold text-ink">{t('reviewTitle')}</h2>
      <p className="text-muted">{t('reviewIntro')}</p>

      <p
        aria-live="polite"
        className={`flex flex-wrap items-center gap-2 rounded-md p-3 font-medium ${unconfirmed > 0 ? 'bg-conditional-soft text-conditional' : 'bg-meets-soft text-meets'}`}
      >
        <StatusIcon kind={unconfirmed > 0 ? 'needsConfirmation' : 'confirmed'} />
        {unconfirmed > 0 ? fill(t('unconfirmedCount'), { n: unconfirmed }) : t('allConfirmed')}
        {checking && <span className="ml-2 text-sm font-normal text-muted">{t('checkingRecords')}</span>}
      </p>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-md border border-short bg-short-soft p-3">
          <p className="flex-1 text-short">{error}</p>
          <button type="button" onClick={() => setError(null)} className="text-sm font-semibold underline">
            {t('dismiss')}
          </button>
        </div>
      )}

      {records.length === 0 && <p className="text-muted">{t('noRecords')}</p>}

      {docIds.map((docId) => {
        const doc = state.documents.find((d) => d.docId === docId)
        const docRecords = records.filter((r) => r.docId === docId)
        return (
          <article key={docId} className="rounded-[var(--radius-card)] border border-line bg-surface p-4 shadow-[var(--shadow-card)]">
            <h3 className="mb-3 font-semibold break-all">
              {doc?.file.name ?? docId}
              <span className="ml-2 text-sm font-normal text-muted">{t(`docType_${docRecords[0].docType}`)}</span>
            </h3>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
              {doc && <Preview doc={doc} />}
              <div className="space-y-4">
                {docRecords.map((record, index) => (
                  <RecordTable
                    key={record.id}
                    record={record}
                    index={index}
                    pages={doc?.result?.pages ?? []}
                    fileName={doc?.file.name ?? docId}
                    onChange={(key, changes) => changeField(record.id, key, changes)}
                  />
                ))}
              </div>
            </div>
          </article>
        )
      })}

      <ExemptionQuestions />

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
          disabled={checking || evaluating || records.length === 0}
          onClick={() => void runEvaluate()}
          className="rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
        >
          {evaluating ? t('evaluating') : t('evaluate')}
        </button>
        <span aria-live="polite" className="sr-only">
          {evaluating ? t('evaluating') : error === t('evaluateError') ? error : ''}
        </span>
      </div>
    </section>
  )
}

interface RecordTableProps {
  record: EvidenceRecord
  index: number
  pages: PageView[]
  fileName: string
  onChange: (key: FieldKey, changes: Partial<AnyField>) => void
}

function RecordTable({ record, index, pages, fileName, onChange }: RecordTableProps) {
  const t = useT()
  const flags = record.flags ?? []
  const [sourceKey, setSourceKey] = useState<FieldKey | null>(null)
  const sourceField = sourceKey ? record[sourceKey] : null
  return (
    <div>
      <h4 className="mb-1 text-sm font-semibold text-muted">
        {fill(t('recordLabel'), { n: index + 1 })}
        {record.issuer.value ? ` · ${record.issuer.value}` : ''}
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th className="py-1 pr-2 font-medium">{t('colField')}</th>
              <th className="py-1 pr-2 font-medium">{t('colValue')}</th>
              <th className="py-1 pr-2 font-medium">{t('colConfidence')}</th>
              <th className="py-1 pr-2 font-medium">{t('colVerification')}</th>
              <th className="hidden py-1 pr-2 font-medium sm:table-cell">{t('colEvidence')}</th>
              <th className="py-1 pr-2 font-medium">{t('colPage')}</th>
              <th className="py-1 font-medium">{t('colAction')}</th>
            </tr>
          </thead>
          <tbody>
            {FIELD_ORDER.map((key) => {
              const field = record[key]
              if (!field) return null
              const label = t(`field_${key}` as MessageKey)
              const flagged = needsConfirmation(field)
              return (
                <tr
                  key={key}
                  className={`border-b border-line align-top ${flagged ? 'bg-conditional-soft shadow-[inset_4px_0_0_var(--color-conditional)]' : ''}`}
                >
                  <th scope="row" className={`py-1.5 pr-2 text-left font-medium ${flagged ? 'pl-2' : ''}`}>
                    {label}
                    {flagged && (
                      <span className="mt-1 flex w-max items-center gap-1 rounded-full border border-conditional bg-surface px-2 py-0.5 text-xs font-semibold text-conditional">
                        <StatusIcon kind="needsConfirmation" className="h-3.5 w-3.5" />
                        {t('needsConfirmation')}
                      </span>
                    )}
                  </th>
                  <td className="tabular py-1.5 pr-2">
                    <FieldEditor
                      key={String(field.value)}
                      kind={FIELD_KIND[key]}
                      value={field.value}
                      label={fill(t('editField'), { field: label })}
                      onCommit={(value) => onChange(key, { value, confirmed: true } as Partial<AnyField>)}
                    />
                    {field.evidence && pages.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setSourceKey(key)}
                        className="mt-1 inline-flex items-center gap-1 rounded-md text-left text-xs font-semibold text-brand-strong underline hover:text-brand"
                      >
                        <FileSearch aria-hidden="true" focusable="false" className="h-3.5 w-3.5 shrink-0" />
                        {fill(t('viewSource'), { field: label })}
                      </button>
                    )}
                    {field.evidence && (
                      // Under 640 px the evidence column is hidden, so the evidence stacks under the value.
                      <p className="mt-1 font-mono text-xs break-words text-muted sm:hidden">
                        <span className="sr-only">{t('colEvidence')}: </span>
                        {field.evidence}
                      </p>
                    )}
                  </td>
                  <td className={`py-1.5 pr-2 ${field.confidence === 'low' ? 'font-semibold text-conditional' : ''}`}>
                    {t(`confidence_${field.confidence}`)}
                  </td>
                  <td className="py-1.5 pr-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs whitespace-nowrap ${VERIFICATION_STYLE[field.verification]}`}>
                      {t(`verification_${field.verification}`)}
                    </span>
                  </td>
                  <td className="hidden py-1.5 pr-2 font-mono text-xs break-words text-muted sm:table-cell">{field.evidence ?? '—'}</td>
                  <td className="py-1.5 pr-2">{field.page}</td>
                  <td className="py-1.5">
                    {field.confirmed ? (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-meets">
                        <StatusIcon kind="confirmed" />
                        {t('confirmedByNavigator')}
                      </span>
                    ) : (
                      <button
                        type="button"
                        aria-label={fill(t('confirmField'), { field: label })}
                        onClick={() => onChange(key, { confirmed: true })}
                        className={`rounded-md px-2 py-1 text-xs font-semibold whitespace-nowrap ${
                          flagged ? 'bg-brand text-white hover:bg-brand-strong' : 'border border-brand text-brand-strong hover:bg-brand-soft'
                        }`}
                      >
                        {t('confirm')}
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {sourceKey && sourceField && (
        <SourceView
          fieldLabel={t(`field_${sourceKey}` as MessageKey)}
          fileName={fileName}
          page={pages.find((p) => p.page === sourceField.page) ?? null}
          evidence={sourceField.evidence}
          onClose={() => setSourceKey(null)}
        />
      )}
      {flags.length > 0 && (
        <div className="mt-2 text-sm">
          <p className="font-medium">{t('flagsLabel')}</p>
          <ul className="list-disc pl-5 text-muted">
            {flags.map((flag, i) => (
              <li key={`${flag.code}-${flag.field ?? ''}-${i}`}>{flag.message}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
