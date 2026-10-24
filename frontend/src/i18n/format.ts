import type { UiLang } from '../state/caseState'

const LOCALES: Record<UiLang, string> = { en: 'en-US', es: 'es-US' }

// "2027-05" -> "May 2027" / "mayo de 2027"
export function formatMonth(month: string, lang: UiLang): string {
  const [year, m] = month.split('-').map(Number)
  if (!year || !m) return month
  return new Intl.DateTimeFormat(LOCALES[lang], { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, m - 1, 1)),
  )
}

// "2027-07-12" -> "July 12, 2027"
export function formatDate(date: string, lang: UiLang): string {
  const [year, m, d] = date.split('-').map(Number)
  if (!year || !m || !d) return date
  return new Intl.DateTimeFormat(LOCALES[lang], { dateStyle: 'long', timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, m - 1, d)),
  )
}

// Integer cents -> "$737.14"
export function formatMoney(cents: number, lang: UiLang): string {
  return new Intl.NumberFormat(LOCALES[lang], { style: 'currency', currency: 'USD' }).format(cents / 100)
}

// Hours with up to 2 decimals.
export function formatHours(hours: number, lang: UiLang): string {
  return new Intl.NumberFormat(LOCALES[lang], { maximumFractionDigits: 2 }).format(hours)
}
