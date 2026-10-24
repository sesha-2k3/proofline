import { Link, Outlet, useLocation } from 'react-router-dom'
import type { MessageKey } from '../i18n/en'
import { useT } from '../i18n/useT'
import { useCaseState, type Step, type UiLang } from '../state/caseState'

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

export function AppShell() {
  const { state, dispatch } = useCaseState()
  const t = useT()
  const onCasePage = useLocation().pathname.startsWith('/case')

  return (
    <div lang={state.lang} className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <Link to="/" className="text-xl font-bold text-brand-strong no-underline">
            {t('appName')}
          </Link>
          {state.demoMode && (
            <span className="rounded-full border border-conditional bg-conditional-soft px-2 py-0.5 text-sm font-medium text-conditional">
              {t('demoMode')}
            </span>
          )}
          <div role="group" aria-label={t('languageLabel')} className="ml-auto flex overflow-hidden rounded-md border border-line">
            {LANGS.map(({ lang, label }) => (
              <button
                key={lang}
                type="button"
                aria-pressed={state.lang === lang}
                onClick={() => dispatch({ type: 'SET_LANG', lang })}
                className={
                  state.lang === lang
                    ? 'bg-brand px-3 py-1 text-sm font-semibold text-white'
                    : 'bg-surface px-3 py-1 text-sm font-semibold text-ink hover:bg-brand-soft'
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {onCasePage && (
          <nav aria-label={t('stepsLabel')} className="mx-auto max-w-5xl px-4 pb-3">
            <ol className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {STEPS.map(({ step, label }) => {
                const current = state.step === step
                return (
                  <li
                    key={step}
                    aria-current={current ? 'step' : undefined}
                    className={current ? 'font-semibold text-brand-strong' : 'text-muted'}
                  >
                    <span
                      className={
                        current
                          ? 'mr-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand text-white'
                          : 'mr-1 inline-flex h-6 w-6 items-center justify-center rounded-full border border-line'
                      }
                    >
                      {step}
                    </span>
                    {t(label)}
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
