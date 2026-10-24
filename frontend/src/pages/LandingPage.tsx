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
    <section className="max-w-2xl">
      <h1 className="text-3xl font-bold text-ink">{t('landingTitle')}</h1>
      <p className="mt-4 text-lg text-muted">{t('landingIntro')}</p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to="/case"
          onClick={reset}
          className="rounded-md bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-strong"
        >
          {t('startCase')}
        </Link>
        <Link
          to="/case?sample=1"
          onClick={reset}
          className="rounded-md border border-brand bg-surface px-5 py-3 font-semibold text-brand-strong hover:bg-brand-soft"
        >
          {t('loadSample')}
        </Link>
      </div>
      <p className="mt-3 text-sm text-muted">{t('sampleNote')}</p>
    </section>
  )
}
