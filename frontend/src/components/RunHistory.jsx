/**
 * RunHistory
 *
 * Paginated table of past runs for a single test case.
 * Each row links to /runs/:id (opens in the same tab; Cmd/Ctrl+click opens a new one).
 *
 * Props:
 *   testCaseId  string
 */

import { useNavigate } from 'react-router-dom'
import { listTestCaseRuns } from '../api/testCases.js'
import Badge   from './ui/Badge.jsx'
import Spinner from './ui/Spinner.jsx'
import Button  from './ui/Button.jsx'
import { useEffect, useState } from 'react'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso) {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

// ── Skeleton row ──────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[40, 56, 64, 56, 56, 56, 64].map((w, i) => (
        <td key={i} className="px-3 py-3">
          <div className={`h-3 bg-gray-100 rounded`} style={{ width: w }} />
        </td>
      ))}
    </tr>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function NoRuns() {
  return (
    <tr>
      <td colSpan={7} className="px-3 py-10 text-center">
        <p className="text-xs text-gray-400">No runs yet. Hit Run to start the first one.</p>
      </td>
    </tr>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function RunHistory({ testCaseId, refreshToken = 0 }) {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [runs, setRuns] = useState([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadRuns() {
      if (!testCaseId) {
        setRuns([])
        setTotal(0)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setIsError(false)
      try {
        const response = await listTestCaseRuns(testCaseId, { page, pageSize })
        if (!cancelled) {
          setRuns(response?.items ?? [])
          setTotal(response?.total ?? 0)
        }
      } catch {
        if (!cancelled) {
          setIsError(true)
          setRuns([])
          setTotal(0)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadRuns()

    return () => {
      cancelled = true
    }
  }, [testCaseId, page, pageSize, refreshToken])

  const pages = Math.ceil(total / pageSize)

  return (
    <div className="flex flex-col gap-3">

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-100">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-3 py-2.5 text-left font-medium text-gray-400 w-10">#</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Date</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Status</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Steps</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Tokens</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Duration</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-400">Provider</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)}
            {isError && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-xs text-red-400">
                  Failed to load run history.
                </td>
              </tr>
            )}
            {!isLoading && !isError && runs.length === 0 && <NoRuns />}
            {runs.map((run, idx) => {
              const runNumber = total - (page - 1) * pageSize - idx
              const isRunning = run.status === 'running'
              return (
                <tr
                  key={run.id}
                  onClick={() => navigate(`/runs/${run.id}`)}
                  className="cursor-pointer hover:bg-gray-50 transition-colors group"
                >
                  <td className="px-3 py-2.5 text-gray-400 tabular-nums">{runNumber}</td>
                  <td className="px-3 py-2.5 text-gray-500">{formatDate(run.started_at)}</td>
                  <td className="px-3 py-2.5">
                    <Badge variant={run.status}>{run.status}</Badge>
                  </td>
                  <td className="px-3 py-2.5 text-gray-500 tabular-nums">
                    {isRunning ? (
                      <Spinner size="xs" className="text-status-running" />
                    ) : (
                      <>
                        <span className="text-status-passed-text font-medium">{run.steps_passed}</span>
                        <span className="text-gray-300 mx-0.5">/</span>
                        <span className="text-status-failed-text font-medium">{run.steps_failed}</span>
                      </>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-gray-500 tabular-nums">
                    {isRunning ? '—' : (run.total_tokens != null ? run.total_tokens.toLocaleString() : '—')}
                  </td>
                  <td className="px-3 py-2.5 text-gray-500 tabular-nums">
                    {formatDuration(run.duration_seconds)}
                  </td>
                  <td className="px-3 py-2.5 text-gray-500">{run.provider ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{total} runs total</span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost" size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Prev
            </Button>
            <span className="px-2 tabular-nums">{page} / {pages}</span>
            <Button
              variant="ghost" size="sm"
              disabled={page === pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
