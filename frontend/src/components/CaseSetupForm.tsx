import { useEffect, useRef, useState, type FormEvent } from 'react'
import { getDeadline, type CaseInfo } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { useT } from '../i18n/useT'
import { useCaseState } from '../state/caseState'
import { Skeleton } from './Skeleton'

const inputClass =
  'mt-1 block w-full max-w-sm rounded-md border border-line bg-surface px-3 py-2 text-ink focus:border-brand'

function formatDate(isoDate: string, lang: CaseInfo['lang']): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString(lang === 'es' ? 'es-US' : 'en-US', {
    timeZone: 'UTC',
    dateStyle: 'long',
  })
}

function validate(info: CaseInfo): MessageKey[] {
  const errors: MessageKey[] = []
  if (!info.clientName.trim()) errors.push('errorClientName')
  if (info.caseType === 'renewal') {
    if (!info.windowStart || !info.windowEnd) errors.push('errorWindow')
    else if (info.windowStart > info.windowEnd) errors.push('errorWindowOrder')
  } else if (!info.applicationMonth) {
    errors.push('errorApplicationMonth')
  }
  return errors
}

export function CaseSetupForm({ onContinue }: { onContinue: () => void }) {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const info = state.caseInfo
  const [errors, setErrors] = useState<MessageKey[]>([])

  // The deadline preview comes from POST /api/deadline. A request counter applies
  // only the newest response; on failure the previous deadline stays as it was.
  const requestSeq = useRef(0)
  useEffect(() => {
    const seq = ++requestSeq.current
    getDeadline({ ...info, clientName: info.clientName.trim(), rfiReceivedDate: info.rfiReceivedDate || null })
      .then((deadline) => seq === requestSeq.current && dispatch({ type: 'SET_DEADLINE', deadline }))
      .catch(() => undefined)
  }, [info, dispatch])

  const update = (changes: Partial<CaseInfo>) => dispatch({ type: 'SET_CASE_INFO', caseInfo: { ...info, ...changes } })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    const found = validate(info)
    setErrors(found)
    if (found.length > 0) return
    // Send only the fields that apply to the chosen case type.
    const renewal = info.caseType === 'renewal'
    dispatch({
      type: 'SET_CASE_INFO',
      caseInfo: {
        ...info,
        clientName: info.clientName.trim(),
        windowStart: renewal ? info.windowStart : null,
        windowEnd: renewal ? info.windowEnd : null,
        applicationMonth: renewal ? null : info.applicationMonth,
        rfiReceivedDate: info.rfiReceivedDate || null,
      },
    })
    onContinue()
  }

  const deadline = state.deadline

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <h2 className="text-xl font-semibold text-ink">{t('setupTitle')}</h2>

      {errors.length > 0 && (
        <div role="alert" className="rounded-md border border-short bg-short-soft p-3 text-short">
          <ul className="list-disc pl-5">
            {errors.map((key) => (
              <li key={key}>{t(key)}</li>
            ))}
          </ul>
        </div>
      )}

      <label className="block">
        <span className="font-medium">{t('clientName')}</span>
        <input
          type="text"
          required
          autoComplete="off"
          value={info.clientName}
          onChange={(e) => update({ clientName: e.target.value })}
          aria-invalid={errors.includes('errorClientName')}
          className={inputClass}
        />
      </label>

      <fieldset>
        <legend className="font-medium">{t('caseType')}</legend>
        <div className="mt-1 flex flex-wrap gap-4">
          {(
            [
              ['renewal', 'caseTypeRenewal'],
              ['new_application', 'caseTypeNewApplication'],
            ] as const
          ).map(([value, label]) => (
            <label key={value} className="flex items-center gap-2">
              <input
                type="radio"
                name="caseType"
                value={value}
                checked={info.caseType === value}
                onChange={() => update({ caseType: value })}
              />
              {t(label)}
            </label>
          ))}
        </div>
      </fieldset>

      {info.caseType === 'renewal' ? (
        <div>
          <div className="flex flex-wrap gap-4">
            <label className="block">
              <span className="font-medium">{t('windowStart')}</span>
              <input
                type="month"
                value={info.windowStart ?? ''}
                onChange={(e) => update({ windowStart: e.target.value || null })}
                aria-invalid={errors.includes('errorWindow') || errors.includes('errorWindowOrder')}
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className="font-medium">{t('windowEnd')}</span>
              <input
                type="month"
                value={info.windowEnd ?? ''}
                onChange={(e) => update({ windowEnd: e.target.value || null })}
                aria-invalid={errors.includes('errorWindow') || errors.includes('errorWindowOrder')}
                className={inputClass}
              />
            </label>
          </div>
          <p className="mt-1 text-sm text-muted">{t('windowHelp')}</p>
        </div>
      ) : (
        <label className="block">
          <span className="font-medium">{t('applicationMonth')}</span>
          <input
            type="month"
            value={info.applicationMonth ?? ''}
            onChange={(e) => update({ applicationMonth: e.target.value || null })}
            aria-invalid={errors.includes('errorApplicationMonth')}
            className={inputClass}
          />
          <span className="mt-1 block text-sm text-muted">{t('applicationHelp')}</span>
        </label>
      )}

      <label className="block">
        <span className="font-medium">{t('rfiReceivedDate')}</span>
        <input
          type="date"
          value={info.rfiReceivedDate ?? ''}
          onChange={(e) => update({ rfiReceivedDate: e.target.value || null })}
          className={inputClass}
        />
      </label>

      {!deadline && !state.rules && <Skeleton lines={2} className="max-w-sm" />}
      {deadline && (
        <div className="rounded-md border border-line bg-surface p-3" aria-live="polite">
          <p className="font-medium">
            {t('responseDeadline')}: {formatDate(deadline.date, info.lang)}
            {deadline.ruleStatus !== 'confirmed' && (
              <span className="ml-2 rounded-full border border-conditional bg-conditional-soft px-2 py-0.5 text-sm text-conditional">
                {t(`ruleStatus_${deadline.ruleStatus}`)}
              </span>
            )}
          </p>
          <p className="mt-1 text-sm text-muted">{t('deadlineNote')}</p>
        </div>
      )}

      <button type="submit" className="rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong">
        {t('continueToDocuments')}
      </button>
    </form>
  )
}
