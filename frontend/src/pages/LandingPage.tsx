import { Link } from 'react-router-dom'
import { useT } from '../i18n/useT'
import { useCaseState } from '../state/caseState'
export function LandingPage() {
  const t = useT()
  const { state, dispatch } = useCaseState()
  const reset = () => {
    state.documents.forEach((d) => URL.revokeObjectURL(d.objectUrl))
    dispatch({ type: 'RESET' })
  }
  return (
    <section className="mx-auto max-w-3xl py-10 sm:py-16">
      <h1 className="text-4xl font-bold leading-tight tracking-tight text-balance break-words text-ink sm:text-5xl">
        {t('tagline')}
      </h1>
      <p className="mt-6 border-l-4 border-brand pl-4 text-xl font-semibold leading-snug text-ink sm:text-2xl">
        {t('problemLine')}
      </p>
      <p className="mt-4 text-lg text-muted">{t('requirementLine')}</p>
      <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Link
          to="/case"
          onClick={reset}
          className="rounded-md bg-brand px-6 py-3 text-center font-semibold text-white shadow-sm hover:bg-brand-strong"
        >
          {t('startCase')}
        </Link>
        <Link
          to="/case?sample=1"
          onClick={reset}
          className="rounded-md border border-brand bg-surface px-6 py-3 text-center font-semibold text-brand-strong hover:bg-brand-soft"
        >
          {t('loadSample')}
        </Link>
      </div>
      <p className="mt-4 text-sm text-muted">{t('sampleNote')}</p>
      <p className="mt-12 border-t border-line pt-6 text-base font-medium text-ink">
        {t('closeLine')}
      </p>
    </section>
  )
}
