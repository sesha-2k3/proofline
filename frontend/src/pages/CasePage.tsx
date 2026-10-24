import { useSearchParams } from 'react-router-dom'
import { useT } from '../i18n/useT'

// Steps 1–5 are filled in by F3–F7.
export function CasePage() {
  const t = useT()
  const [params] = useSearchParams()
  const isSample = params.get('sample') === '1'

  return (
    <section>
      <h1 className="text-2xl font-bold text-ink">{isSample ? t('sampleCaseTitle') : t('caseTitle')}</h1>
      <p className="mt-4 text-muted">{t('comingSoon')}</p>
    </section>
  )
}
