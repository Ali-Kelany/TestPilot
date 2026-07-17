/**
 * ScreenshotViewer
 *
 * Displays screenshots captured during a live run.
 * Screenshots are NOT streamed over WebSocket — they are stored in the DB
 * and fetched via REST after each step completes.
 *
 * Strategy:
 *   1. Count completed steps from the events array.
 *   2. Whenever that count increases, refetch the screenshot list.
 *   3. Show the two most recent screenshots (obs + verify for the last
 *      completed step) as large previews.
 *   4. Show earlier steps as a scrollable thumbnail strip below.
 *
 * Screenshots are grouped in pairs: even index = observation, odd = verification.
 *
 * Props:
 *   sessionId   string | null   — run UUID (= session_id from execution.started)
 *   events      WsEvent[]
 */

import { useEffect, useState } from 'react'
import { getScreenshots, screenshotUrl } from '../api/testRuns.js'
import Spinner from './ui/Spinner.jsx'

// ── Count how many steps have completed (drives refetch) ──────────────────────

function countCompletedSteps(events) {
  return events.filter((ev) => ev.type === 'step.completed').length
}

// ── Single screenshot tile ────────────────────────────────────────────────────

function ScreenshotTile({ runId, screenshotId, kind, stepNumber, active = false, small = false }) {
  return (
    <div
      className={`
        flex flex-col gap-1 rounded-lg overflow-hidden border transition-colors
        ${active ? 'border-status-running' : 'border-gray-100'}
        ${small ? 'w-24 shrink-0' : 'flex-1'}
      `}
    >
      <img
        src={screenshotUrl(runId, screenshotId)}
        alt={`Step ${stepNumber} ${kind}`}
        className={`
          w-full object-cover bg-gray-100
          ${small ? 'h-14' : 'h-36'}
        `}
        loading="lazy"
      />
      <div className="px-1.5 pb-1.5 flex items-center justify-between">
        <span className="text-2xs text-gray-400">
          {small ? `S${stepNumber}` : `Step ${stepNumber}`}
        </span>
        <span className={`text-2xs font-medium ${kind === 'observation' ? 'text-gray-400' : 'text-status-passed-text'}`}>
          {kind === 'observation' ? 'obs' : 'verify'}
        </span>
      </div>
    </div>
  )
}

// ── Empty / loading states ────────────────────────────────────────────────────

function WaitingState() {
  return (
    <div className="flex items-center justify-center h-24 rounded-lg bg-gray-50 border border-gray-100 border-dashed">
      <p className="text-2xs text-gray-300 italic">Screenshots will appear after each step</p>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function ScreenshotViewer({ sessionId, events }) {
  const completedSteps = countCompletedSteps(events)
  const [screenshots, setScreenshots] = useState([])
  const [isFetching, setIsFetching] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadScreenshots() {
      if (!sessionId || completedSteps === 0) {
        setScreenshots([])
        setIsFetching(false)
        return
      }

      setIsFetching(true)
      try {
        const response = await getScreenshots(sessionId)
        if (!cancelled) {
          setScreenshots(response?.screenshots ?? [])
        }
      } finally {
        if (!cancelled) {
          setIsFetching(false)
        }
      }
    }

    loadScreenshots()

    return () => {
      cancelled = true
    }
  }, [sessionId, completedSteps])

  if (!sessionId || completedSteps === 0) return <WaitingState />

  if (isFetching && screenshots.length === 0) {
    return (
      <div className="flex items-center gap-2 h-24 rounded-lg bg-gray-50 border border-gray-100 px-4">
        <Spinner size="sm" className="text-gray-300" />
        <span className="text-2xs text-gray-300">Loading screenshots…</span>
      </div>
    )
  }

  if (screenshots.length === 0) return <WaitingState />

  // The last two screenshots are the most recent step's pair
  const recentTwo = screenshots.slice(-2)
  const earlier   = screenshots.slice(0, -2)

  // Group earlier ones into step pairs for the thumbnail strip
  const pairs = []
  for (let i = 0; i < earlier.length; i += 2) {
    if (earlier[i]) pairs.push(earlier[i])
    if (earlier[i + 1]) pairs.push(earlier[i + 1])
  }

  return (
    <div className="space-y-2">

      {/* Most recent step — large preview */}
      <div className="flex gap-2">
        {recentTwo.map((ss) => (
          <ScreenshotTile
            key={ss.id}
            runId={sessionId}
            screenshotId={ss.id}
            kind={ss.kind}
            stepNumber={ss.step_number}
            active={isFetching}
          />
        ))}
        {/* Placeholder if we only have one so far */}
        {recentTwo.length === 1 && (
          <div className="flex-1 rounded-lg bg-gray-50 border border-dashed border-gray-100 flex items-center justify-center">
            <Spinner size="sm" className="text-gray-200" />
          </div>
        )}
      </div>

      {/* Earlier steps — scrollable thumbnail strip */}
      {pairs.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {pairs.map((ss) => (
            <ScreenshotTile
              key={ss.id}
              runId={sessionId}
              screenshotId={ss.id}
              kind={ss.kind}
              stepNumber={ss.step_number}
              small
            />
          ))}
        </div>
      )}
    </div>
  )
}
