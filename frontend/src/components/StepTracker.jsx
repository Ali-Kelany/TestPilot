/**
 * StepTracker
 *
 * Horizontal row of numbered bubbles — one per step.
 * State is derived entirely from the accumulated WS events array;
 * no internal state needed.
 *
 * Bubble states
 *   pending  — not reached yet                (gray ring)
 *   active   — step.started received          (blue, pulsing ring)
 *   passed   — step.completed, status=passed  (green ✓)
 *   failed   — step.completed, status=failed  (red ✗)
 *
 * Props:
 *   events      WsEvent[]   — full accumulated event list
 *   totalSteps  number      — from execution.started.total_steps
 */

// ── Derive per-step state from events ────────────────────────────────────────

function deriveSteps(events, totalSteps) {
  const steps = Array.from({ length: totalSteps }, (_, i) => ({
    number: i + 1,
    state: 'pending',   // 'pending' | 'active' | 'passed' | 'failed'
  }))

  for (const ev of events) {
    if (ev.type === 'step.started') {
      const idx = (ev.step_index ?? 1) - 1
      if (steps[idx]) steps[idx].state = 'active'
    }
    if (ev.type === 'step.completed') {
      const idx = (ev.step_index ?? 1) - 1
      if (steps[idx]) {
        steps[idx].state = ev.passed !== false ? 'passed' : 'failed'
      }
    }
  }

  return steps
}

// ── Bubble ────────────────────────────────────────────────────────────────────

function Bubble({ number, state }) {
  const base = 'relative flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-2xs font-semibold transition-all duration-300'

  const styles = {
    pending: `${base} border-2 border-gray-200 text-gray-400`,
    active:  `${base} border-2 border-status-running bg-status-running-bg text-status-running-text ring-pulse`,
    passed:  `${base} bg-status-passed-bg border-2 border-status-passed text-status-passed-text`,
    failed:  `${base} bg-status-failed-bg border-2 border-status-failed text-status-failed-text`,
  }

  const icon = {
    passed: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
      </svg>
    ),
    failed: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12"/>
      </svg>
    ),
  }

  return (
    <div className={styles[state]} title={`Step ${number}: ${state}`}>
      {icon[state] ?? number}
    </div>
  )
}

// ── Connector line between bubbles ────────────────────────────────────────────

function Line({ leftState }) {
  const filled = leftState === 'passed' || leftState === 'failed'
  return (
    <div className={`h-0.5 flex-1 min-w-[8px] rounded-full transition-colors duration-500 ${filled ? 'bg-gray-300' : 'bg-gray-100'}`} />
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function StepTracker({ events, totalSteps }) {
  if (!totalSteps) return null

  const steps = deriveSteps(events, totalSteps)

  return (
    <div className="flex items-center gap-1.5" role="list" aria-label="Step progress">
      {steps.map((step, i) => (
        <div key={step.number} className="contents">
          <Bubble number={step.number} state={step.state} />
          {i < steps.length - 1 && <Line leftState={step.state} />}
        </div>
      ))}
    </div>
  )
}
