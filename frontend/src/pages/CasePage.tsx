import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getRules, getSamples, type SamplesResponse } from '../api/client'
import { CaseSetupForm } from '../components/CaseSetupForm'
import { PossibleExemptionNotice } from '../components/ExemptionQuestions'
import { GapList } from '../components/GapList'
import { MonthCards } from '../components/MonthCards'
import { PacketPanel } from '../components/PacketPanel'
import { ReviewPanel } from '../components/ReviewPanel'
import { Uploader } from '../components/Uploader'
import { formatDate } from '../i18n/format'
import { fill, useT } from '../i18n/useT'
import { useCaseState, type Step } from '../state/caseState'

// Case steps 1–5 (F3–F7).
export function CasePage() {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const [params] = useSearchParams()
  const isSample = params.get('sample') === '1'
  const [samples, setSamples] = useState<SamplesResponse | null>(null)
  const [sampleError, setSampleError] = useState(false)
  const sampleRequested = useRef(false)

  // Rules (thresholds and statuses) are needed for the deadline preview and later steps.
  useEffect(() => {
    if (state.rules) return
    let cancelled = false
    getRules()
      .then((rules) => !cancelled && dispatch({ type: 'SET_RULES', rules }))
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [state.rules, dispatch])

  // Sample mode: prefill the case from GET /api/samples (keeps the chosen language).
  const lang = state.caseInfo.lang
  useEffect(() => {
    if (!isSample || sampleRequested.current) return
    sampleRequested.current = true
    getSamples()
      .then((response) => {
        setSamples(response)
        if (state.documents.length === 0) dispatch({ type: 'SET_CASE_INFO', caseInfo: { ...response.caseInfo, lang } })
      })
      .catch(() => setSampleError(true))
  }, [isSample, lang, state.documents.length, dispatch])

  const setStep = (step: Step) => dispatch({ type: 'SET_STEP', step })

  // Keyboard and screen reader users land at the top of each new step.
  const headingRef = useRef<HTMLHeadingElement>(null)
  const firstStep = useRef(true)
  useEffect(() => {
    if (firstStep.current) {
      firstStep.current = false
      return
    }
    window.scrollTo(0, 0)
    headingRef.current?.focus()
  }, [state.step])

  return (
    <section className="space-y-6">
      <h1 ref={headingRef} tabIndex={-1} className="text-2xl font-bold text-ink">{isSample ? t('sampleCaseTitle') : t('caseTitle')}</h1>

      {isSample && !samples && !sampleError && (
        <p role="status" className="text-muted">
          {t('sampleLoading')}
        </p>
      )}
      {sampleError && (
        <div role="alert" className="flex items-start gap-3 rounded-md border border-short bg-short-soft p-3">
          <p className="flex-1 text-short">{t('sampleLoadError')}</p>
          <button type="button" onClick={() => setSampleError(false)} className="text-sm font-semibold underline">
            {t('dismiss')}
          </button>
        </div>
      )}

      {state.step === 1 && <CaseSetupForm onContinue={() => setStep(2)} />}
      {state.step === 2 && (
        <Uploader samples={isSample ? samples : null} onBack={() => setStep(1)} onContinue={() => setStep(3)} />
      )}
      {state.step === 3 && <ReviewPanel onBack={() => setStep(2)} onEvaluated={() => setStep(4)} />}
      {state.step === 4 && <ResultsStep onBack={() => setStep(3)} onContinue={() => setStep(5)} />}
      {state.step === 5 && <PacketPanel onBack={() => setStep(4)} />}
    </section>
  )
}

// Step 4 (F6): summary, deadline, month cards, gaps, possible exemptions.
function ResultsStep({ onBack, onContinue }: { onBack: () => void; onContinue: () => void }) {
  const t = useT()
  const { state } = useCaseState()
  const evaluation = state.evaluation
  const lang = state.caseInfo.lang

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold text-ink">{t('resultsTitle')}</h2>

      {evaluation && (
        <>
          <div className="space-y-2 rounded-lg border border-line bg-surface p-4">
            <h3 className="text-lg font-semibold">{t('summaryTitle')}</h3>
            <p aria-live="polite">{evaluation.summary}</p>
            {evaluation.deadline && (
              <p className="font-medium">
                {fill(t('deadlineLine'), { date: formatDate(evaluation.deadline.date, lang) })}
                {evaluation.deadline.ruleStatus !== 'confirmed' && (
                  <span className="ml-2 rounded-full bg-conditional-soft px-2 py-0.5 text-sm text-conditional">
                    {t(`ruleStatus_${evaluation.deadline.ruleStatus}`)}
                  </span>
                )}
              </p>
            )}
          </div>

          <MonthCards evaluation={evaluation} />
          <GapList gaps={evaluation.gaps} />

          {evaluation.possibleExemptions.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-lg font-semibold">{t('possibleExemptionsTitle')}</h3>
              {evaluation.possibleExemptions.map((e) => (
                <PossibleExemptionNotice key={e.id} exemption={e} />
              ))}
            </section>
          )}
        </>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md border border-brand bg-surface px-5 py-3 font-semibold text-brand-strong hover:bg-brand-soft"
        >
          {t('backToReview')}
        </button>
        <button
          type="button"
          disabled={!evaluation}
          onClick={onContinue}
          className="rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong disabled:opacity-50"
        >
          {t('continueToPacket')}
        </button>
      </div>
    </section>
  )
}
