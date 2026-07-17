/**
 * LiveRunPanel
 *
 * Shown in the TestCaseDetail body section while a WebSocket run is active.
 * Replaces the RunHistory table for the duration of the run.
 *
 * Derives all display state from the accumulated events array — no extra
 * fetching or internal state needed beyond what the sub-components do.
 *
 * Layout (stacked):
 *   ┌─ Step tracker: bubble progress bar ─────────────────┐
 *   ├─ Event feed: scrolling event log ───────────────────┤
 *   └─ Screenshot viewer: obs+verify pair + thumb strip ──┘
 *
 * Props:
 *   events     WsEvent[]
 *   sessionId  string | null
 *   onStop     () => void
 */

import { useMemo } from 'react'
import StepTracker      from './StepTracker.jsx'
import EventFeed        from './EventFeed.jsx'
import ScreenshotViewer from './ScreenshotViewer.jsx'
import Badge            from './ui/Badge.jsx'
import Button           from './ui/Button.jsx'

// ── Derive total steps from execution.started event ───────────────────────────

function getTotalSteps(events) {
  const ev = events.find((e) => e.type === 'execution.started')
  return ev?.test_case?.total_steps ?? 0
}

// ── Derive final verdict (once execution.completed arrives) ───────────────────

function getFinalVerdict(events) {
  const ev = events.find((e) => e.type === 'execution.completed')
  if (!ev) return null
  return { status: ev.result, passed: ev.steps?.passed ?? 0, failed: ev.steps?.failed ?? 0 }
}

// ── Verdict banner shown when run finishes (socket closes after this) ─────────

function VerdictBanner({ verdict }) {
  const ok = verdict.status === 'passed'
  return (
    <div className={`
      flex items-center gap-3 rounded-lg px-4 py-3 border
      ${ok
        ? 'bg-status-passed-bg border-status-passed/30 text-status-passed-text'
        : 'bg-status-failed-bg border-status-failed/30 text-status-failed-text'
      }
    `}>
      <span className="text-xl">{ok ? '✓' : '✗'}</span>
      <div>
        <p className="text-sm font-semibold">
          {ok ? 'All steps passed' : 'Run failed'}
        </p>
        <p className="text-2xs opacity-75 mt-0.5">
          {verdict.passed} passed · {verdict.failed} failed
        </p>
      </div>
    </div>
  )
}

// ── Section label ─────────────────────────────────────────────────────────────

function SectionLabel({ children }) {
  return (
    <p className="text-2xs font-semibold text-gray-400 uppercase tracking-wider">
      {children}
    </p>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function LiveRunPanel({ events, sessionId, onStop }) {
  const totalSteps = useMemo(() => getTotalSteps(events), [events])
  const verdict    = useMemo(() => getFinalVerdict(events), [events])
  const isComplete = verdict !== null

  return (
    <div className="flex flex-col gap-5">

      {/* ── Step tracker ──────────────────────────────────────────────────── */}
      {totalSteps > 0 && (
        <div className="space-y-2">
          <SectionLabel>Progress</SectionLabel>
          <StepTracker events={events} totalSteps={totalSteps} />
        </div>
      )}

      {/* ── Verdict banner (once execution.completed arrives) ─────────────── */}
      {isComplete && <VerdictBanner verdict={verdict} />}

      {/* ── Event feed ────────────────────────────────────────────────────── */}
      <EventFeed events={events} />

      {/* ── Screenshots ───────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <SectionLabel>Screenshots</SectionLabel>
        <ScreenshotViewer sessionId={sessionId} events={events} />
      </div>

      {/* ── Stop watching button (shown only while still running) ─────────── */}
      {!isComplete && (
        <div className="flex items-center gap-3 pt-1">
          <Button variant="ghost" size="sm" onClick={onStop} className="text-gray-400">
            Stop watching
          </Button>
          <p className="text-2xs text-gray-400 italic">
            Closing this or stopping will abort the active run.
          </p>
        </div>
      )}
    </div>
  )
}
