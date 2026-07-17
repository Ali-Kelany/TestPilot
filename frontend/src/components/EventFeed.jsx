/**
 * EventFeed
 *
 * Scrolling log of all WS events received during a live run.
 * Auto-scrolls to the bottom as new events arrive; pauses when
 * the user scrolls up to read something; resumes when they
 * scroll back to the bottom.
 *
 * Each event type has its own visual row style — the feed functions
 * as a real-time transcript of everything the agent is doing.
 *
 * Props:
 *   events  WsEvent[]
 */

import { useEffect, useRef, useState, useCallback } from 'react'

// ── Event → row config ────────────────────────────────────────────────────────

function rowConfig(ev) {
  switch (ev.type) {

    case 'execution.started':
      return {
        tag: 'start', tagCls: 'bg-gray-100 text-gray-500',
        text: `Starting execution${ev.test_case?.total_steps ? ` — ${ev.test_case.total_steps} steps` : ''}`,
        textCls: 'text-gray-500 italic',
      }

    case 'step.started':
      return {
        tag: `step ${ev.step_index ?? '?'}/${ev.total_steps ?? '?'}`,
        tagCls: 'bg-status-running-bg text-status-running-text',
        text: ev.action ?? '',
        textCls: 'text-gray-800 font-medium',
        bold: true,
      }

    case 'step.completed': {
      const passed = ev.passed !== false
      return {
        tag: passed ? 'done ✓' : 'done ✗',
        tagCls: passed ? 'bg-status-passed-bg text-status-passed-text' : 'bg-status-failed-bg text-status-failed-text',
        text: ev.reason ?? (passed ? 'Step passed' : 'Step failed'),
        textCls: passed ? 'text-status-passed-text' : 'text-status-failed-text',
        indent: true,
      }
    }

    case 'agent.tool.called':
      return {
        tag: 'tool',
        tagCls: 'bg-gray-100 text-gray-400 border border-gray-200',
        text: `→ ${ev.tool_name ?? ''}(${ev.tool_args ? JSON.stringify(ev.tool_args) : ''})`,
        textCls: 'text-gray-500 font-mono',
        indent: true,
      }

    case 'agent.tool.result': {
      const ok = ev.success !== false
      return {
        tag: ok ? 'ok' : 'err',
        tagCls: ok ? 'bg-status-passed-bg text-status-passed-text' : 'bg-status-failed-bg text-status-failed-text',
        text: `← ${typeof ev.result === 'string' ? ev.result : JSON.stringify(ev.result) ?? ''}`,
        textCls: ok ? 'text-gray-600 font-mono' : 'text-status-failed-text font-mono',
        indent: true,
      }
    }

    case 'verification': {
      const passed = ev.passed !== false
      return {
        tag: passed ? 'verify ✓' : 'verify ✗',
        tagCls: passed ? 'bg-status-passed-bg text-status-passed-text' : 'bg-status-failed-bg text-status-failed-text',
        text: ev.reason ?? ev.assertion ?? '',
        textCls: passed ? 'text-status-passed-text' : 'text-status-failed-text',
        indent: true,
      }
    }

    case 'recovery':
      return {
        tag: `retry ${ev.retry_count ?? '?'}/${ev.max_retries ?? '?'}`,
        tagCls: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
        text: ev.reason ?? 'Retrying…',
        textCls: 'text-yellow-700',
        indent: true,
      }

    case 'log': {
      const level = (ev.level ?? 'info').toLowerCase()
      const textCls =
        level === 'error'   ? 'text-status-failed-text' :
        level === 'warning' ? 'text-yellow-600' :
                              'text-gray-400'
      return {
        tag: level,
        tagCls: 'bg-transparent text-gray-300',
        text: ev.message ?? '',
        textCls: `${textCls} font-mono`,
        indent: true,
        logLevel: level,
      }
    }

    case 'execution.completed': {
      const passed = ev.result === 'passed'
      return {
        tag: ev.result ?? 'done',
        tagCls: passed ? 'bg-status-passed-bg text-status-passed-text' : 'bg-status-failed-bg text-status-failed-text',
        text: passed
          ? `All steps passed — ${ev.steps?.passed ?? 0} / ${(ev.steps?.passed ?? 0) + (ev.steps?.failed ?? 0)}`
          : `${ev.steps?.failed ?? '?'} step(s) failed`,
        textCls: `${passed ? 'text-status-passed-text' : 'text-status-failed-text'} font-semibold`,
        bold: true,
      }
    }

    case 'error':
      return {
        tag: 'error',
        tagCls: 'bg-status-failed-bg text-status-failed-text',
        text: ev.message ?? 'An error occurred',
        textCls: 'text-status-failed-text font-medium',
      }

    default:
      return {
        tag: ev.type,
        tagCls: 'bg-gray-100 text-gray-400',
        text: JSON.stringify(ev),
        textCls: 'text-gray-400 font-mono',
      }
  }
}

// ── Single row ────────────────────────────────────────────────────────────────

function EventRow({ ev }) {
  const cfg = rowConfig(ev)

  return (
    <div className={`flex gap-2 items-baseline leading-relaxed ${cfg.indent ? 'pl-2' : ''}`}>
      <span className={`shrink-0 rounded px-1 py-px text-2xs font-medium leading-none mt-0.5 ${cfg.tagCls}`}>
        {cfg.tag}
      </span>
      <span className={`text-xs break-words min-w-0 ${cfg.textCls}`}>
        {cfg.text}
      </span>
    </div>
  )
}

// ── Log-level filter pill ─────────────────────────────────────────────────────

const LOG_LEVELS = ['all', 'info', 'warning', 'error']

function LevelFilter({ value, onChange }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-2xs text-gray-400 mr-0.5">logs</span>
      {LOG_LEVELS.map((l) => (
        <button
          key={l}
          onClick={() => onChange(l)}
          className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
            value === l
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function EventFeed({ events }) {
  const containerRef   = useRef(null)
  const isAtBottomRef  = useRef(true)
  const [logLevel, setLogLevel] = useState('all')

  // Track whether the user has scrolled away from the bottom
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const threshold = 40   // px from the bottom — forgiveness zone
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
  }, [])

  // Auto-scroll on new events — only if the user hasn't scrolled up
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    if (isAtBottomRef.current) {
      el.scrollTop = el.scrollHeight
    }
  }, [events])

  // Filter: hide log rows that don't match the selected level
  const visible = events.filter((ev) => {
    if (ev.type === 'done') return false   // terminal wrapper — nothing to show
    if (ev.type !== 'log' || logLevel === 'all') return true
    return (ev.level ?? 'info').toLowerCase() === logLevel
  })

  return (
    <div className="flex flex-col gap-1.5">

      {/* Filter bar */}
      <div className="flex items-center justify-between">
        <span className="text-2xs font-semibold text-gray-400 uppercase tracking-wider">
          Event feed
        </span>
        <LevelFilter value={logLevel} onChange={setLogLevel} />
      </div>

      {/* Feed */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="
          h-52 overflow-y-auto rounded-lg bg-gray-50 border border-gray-100
          px-3 py-2.5 space-y-1.5
        "
      >
        {visible.length === 0 ? (
          <p className="text-2xs text-gray-300 italic">Waiting for events…</p>
        ) : (
          visible.map((ev, i) => <EventRow key={ev.event_id ?? i} ev={ev} />)
        )}
      </div>
    </div>
  )
}
