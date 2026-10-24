import { useEffect } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { getHealth } from '../api/client'
import type { MessageKey } from '../i18n/en'
import { useT } from '../i18n/useT'
import { useCaseState, type Step, type UiLang } from '../state/caseState'
import { StatusIcon } from './StatusIcon'

const STEPS: { step: Step; label: MessageKey }[] = [
  { step: 1, label: 'stepCase' },
  { step: 2, label: 'stepDocuments' },
  { step: 3, label: 'stepReview' },
  { step: 4, label: 'stepResults' },
  { step: 5, label: 'stepPacket' },
]

const LANGS: { lang: UiLang; label: string }[] = [
  { lang: 'en', label: 'EN' },
  { lang: 'es', label: 'ES' },
]


const FOCUS = 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

export function AppShell() {
  const { state, dispatch } = useCaseState()
  const t = useT()
  const onCasePage = useLocation().pathname.startsWith('/case')
  const lang = state.caseInfo.lang

  // Health check once on load: shows the Demo mode badge, or a warning if the server is unreachable.
  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((health) => !cancelled && dispatch({ type: 'SET_HEALTH', health }))
      .catch(() => !cancelled && dispatch({ type: 'SET_HEALTH', health: null, error: true }))
    return () => {
      cancelled = true
    }
  }, [dispatch])

  return (
    <div lang={lang} className="min-h-screen">
      <header className="border-b border-line bg-surface shadow-sm">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <Link to="/" className={`flex items-center gap-2 rounded text-xl font-bold text-brand-strong no-underline ${FOCUS}`}>
            <span aria-hidden="true" className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-brand text-white">
              <StatusIcon kind="check" />
            </span>
            {t('appName')}
          </Link>
          {state.health?.demoMode && (
            <span className="rounded-full border border-conditional bg-conditional-soft px-2 py-0.5 text-sm font-medium text-conditional">
              {t('demoMode')}
            </span>
          )}
          {state.healthError && (
            <span role="status" className="rounded-full border border-short bg-short-soft px-2 py-0.5 text-sm font-medium text-short">
              {t('serverOffline')}
            </span>
          )}
          <div role="group" aria-label={t('languageLabel')} className="ml-auto flex overflow-hidden rounded-md border border-line">
            {LANGS.map(({ lang: option, label }) => (
              <button
                key={option}
                type="button"
                aria-pressed={option === lang}
                onClick={() => dispatch({ type: 'SET_LANG', lang: option })}
                className={`px-3 py-1 text-sm font-semibold focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-strong ${
                  option === lang ? 'bg-brand text-white' : 'bg-surface text-ink hover:bg-brand-soft'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {onCasePage && (
          <nav aria-label={t('stepsLabel')} className="mx-auto max-w-5xl px-2 pt-1 pb-3 sm:px-4">
            <ol className="flex w-full text-xs sm:text-sm">
              {STEPS.map(({ step, label }) => {
                const current = state.step === step
                const done = step < state.step
                return (
                  <li
                    key={step}
                    aria-current={current ? 'step' : undefined}
                    className="relative flex min-w-0 flex-1 flex-col items-center gap-1 text-center"
                  >
                    {step > 1 && (
                      <span
                        aria-hidden="true"
                        className={`absolute top-3 right-1/2 left-[-50%] h-0.5 ${step <= state.step ? 'bg-brand' : 'bg-line'}`}
                      />
                    )}
                    <span
                      aria-hidden="true"
                      className={`relative z-10 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                        done
                          ? 'bg-brand text-white'
                          : current
                            ? 'bg-brand text-white ring-4 ring-brand-soft'
                            : 'border border-line bg-surface text-muted'
                      }`}
                    >
                      {done ? <StatusIcon kind="check" /> : step}
                    </span>
                    <span
                      className={`break-words px-0.5 leading-tight ${
                        current ? 'font-semibold text-brand-strong' : done ? 'text-ink' : 'text-muted'
                      }`}
                    >
                      {t(label)}
                    </span>
                  </li>
                )
              })}
            </ol>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
