import {
  Calendar,
  Check,
  CircleCheck,
  CircleMinus,
  CircleQuestionMark,
  CircleX,
  LoaderCircle,
  Star,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'

export type StatusIconKind =
  | 'meets'
  | 'conditional'
  | 'short'
  | 'ok'
  | 'warning'
  | 'failed'
  | 'skipped'
  | 'working'
  | 'needsConfirmation'
  | 'confirmed'
  | 'best'
  | 'calendar'
  | 'check'

// lucide 1.x names: CircleCheck (was CheckCircle2), TriangleAlert (was AlertTriangle).
const ICONS: Record<StatusIconKind, LucideIcon> = {
  meets: CircleCheck,
  conditional: CircleQuestionMark,
  short: CircleX,
  ok: CircleCheck,
  warning: TriangleAlert,
  failed: CircleX,
  skipped: CircleMinus,
  working: LoaderCircle,
  needsConfirmation: TriangleAlert,
  confirmed: CircleCheck,
  best: Star,
  calendar: Calendar,
  check: Check,
}

// One icon set for every status. Decorative only: the text label next to it carries the meaning.
export function StatusIcon({ kind, className = 'h-4 w-4' }: { kind: StatusIconKind; className?: string }) {
  const Icon = ICONS[kind]
  const spin = kind === 'working' ? ' motion-safe:animate-spin' : ''
  return <Icon aria-hidden="true" focusable="false" className={`shrink-0 ${className}${spin}`} strokeWidth={2.25} />
}
