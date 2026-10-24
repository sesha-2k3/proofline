import type { RulesResponse } from '../api/client'
import { useT } from '../i18n/useT'
import { useCaseState } from '../state/caseState'

type PossibleExemption = RulesResponse['exemptionQuestions'][number]

// Shown for a "yes" answer and in results. Never says "exempt": the navigator confirms.
export function PossibleExemptionNotice({ exemption }: { exemption: PossibleExemption }) {
  const t = useT()
  return (
    <p className="mt-2 rounded-md border border-conditional bg-conditional-soft p-2 text-sm text-conditional">
      <span className="font-semibold">{t('possibleExemption')}</span>
      <span className="block text-ink">{exemption.label}</span>
      <span className="block">
        {t('sourceLabel')}:{' '}
        <a href={exemption.sourceUrl} target="_blank" rel="noreferrer" className="font-medium text-brand-strong underline">
          {exemption.source}
        </a>
      </span>
    </p>
  )
}

export function ExemptionQuestions() {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const questions = state.rules?.exemptionQuestions ?? []
  if (questions.length === 0) return null

  const answerFor = (id: string) => state.exemptionAnswers.find((a) => a.id === id)?.answer

  return (
    <section className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] p-4">
      <h3 className="text-lg font-semibold">{t('exemptionsTitle')}</h3>
      <p className="text-sm text-muted">{t('exemptionsIntro')}</p>
      <ul className="space-y-3">
        {questions.map((q) => {
          const answer = answerFor(q.id)
          return (
            <li key={q.id}>
              <fieldset>
                <legend className="font-medium">{q.label}</legend>
                <div className="mt-1 flex gap-4">
                  {([true, false] as const).map((value) => (
                    <label key={String(value)} className="flex items-center gap-1.5">
                      <input
                        type="radio"
                        name={`exemption-${q.id}`}
                        checked={answer === value}
                        onChange={() => dispatch({ type: 'SET_EXEMPTION_ANSWER', answer: { id: q.id, answer: value } })}
                      />
                      {value ? t('yes') : t('no')}
                    </label>
                  ))}
                </div>
              </fieldset>
              {answer === true && <PossibleExemptionNotice exemption={q} />}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
