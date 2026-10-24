import { useT } from '../i18n/useT'
// Loading placeholder (Requirement 9.5): gray blocks that pulse only under motion-safe,
// with visually hidden "Loading" text for screen readers.
export function Skeleton({ lines = 1, className = '' }: { lines?: number; className?: string }) {
  const t = useT()
  return (
    <div role="status" className={`space-y-2 ${className}`}>
      <span className="sr-only">{t('loading')}</span>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className={`h-4 rounded-[var(--radius-card)] bg-[var(--color-skeleton)] motion-safe:animate-pulse ${i === lines - 1 && lines > 1 ? 'w-2/3' : 'w-full'}`}
        />
      ))}
    </div>
  )
}
// Inline variant for short values inside a line of text (e.g. the countdown).
// No role of its own: it usually sits inside an existing status region.
export function InlineSkeleton({ className = 'w-16' }: { className?: string }) {
  const t = useT()
  return (
    <span className="inline-flex items-center">
      <span className="sr-only">{t('loading')}</span>
      <span
        aria-hidden="true"
        className={`inline-block h-4 rounded-[var(--radius-card)] bg-[var(--color-skeleton)] motion-safe:animate-pulse ${className}`}
      />
    </span>
  )
}
