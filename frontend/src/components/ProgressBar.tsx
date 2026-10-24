// Horizontal bar for counted hours against the hours threshold.
// The fill is a scaleX transform so the change from the prior value animates
// (about 600 ms); reduced motion shows the new value at once.
export function ProgressBar({
  value,
  max,
  fraction,
  label,
}: {
  value: number
  max: number
  fraction: number
  label: string
}) {
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuetext={label}
      aria-label={label}
      className="h-2.5 w-full overflow-hidden rounded-full bg-line/50"
    >
      <div
        className="h-full w-full origin-left rounded-full bg-brand transition-transform duration-[600ms] ease-out motion-reduce:transition-none"
        style={{ transform: `scaleX(${fraction})` }}
      />
    </div>
  )
}
