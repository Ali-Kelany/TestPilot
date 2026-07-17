
import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  getTestRun,
  getScreenshots,
  getLogs,
  deleteTestRun,
  screenshotUrl,
} from '../api/testRuns.js'
import Badge   from '../components/ui/Badge.jsx'
import Button  from '../components/ui/Button.jsx'
import Modal   from '../components/ui/Modal.jsx'
import Spinner from '../components/ui/Spinner.jsx'

// ── Helpers to know start at and finish at ───────────────────────────────────────────────────────────────────

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function duration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

// ── Page-level skeleton ───────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 animate-pulse">
      <div className="border-b border-gray-200 bg-white h-14" />
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-white border border-gray-100" />
          ))}
        </div>
        <div className="h-48 rounded-xl bg-white border border-gray-100" />
        <div className="h-64 rounded-xl bg-white border border-gray-100" />
      </div>
    </div>
  )
}

// ── Stat box is to make box in details

function StatBox({ label, value, valueClass = 'text-gray-900' }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-5 py-4">
      <p className="text-2xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">{label}</p>
      <p className={`text-2xl font-semibold tabular-nums leading-none ${valueClass}`}>{value}</p>
    </div>
  )
}

// ── Section card wrapper ──────────────────────────────────────────────────────

function Section({ title, children, action }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title}</h2>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

// ── Step results table ────────────────────────────────────────────────────────

function StepResultsTable({ stepResults, testCaseSteps }) {
  if (!stepResults?.length) {
    return <p className="text-xs text-gray-400">No step results recorded.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="pb-2 text-left font-medium text-gray-400 w-10">#</th>
            <th className="pb-2 text-left font-medium text-gray-400">Action</th>
            <th className="pb-2 text-left font-medium text-gray-400">Assertion</th>
            <th className="pb-2 text-left font-medium text-gray-400 w-20">Status</th>
            <th className="pb-2 text-left font-medium text-gray-400 w-16">Retries</th>
            <th className="pb-2 text-left font-medium text-gray-400">Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {stepResults.map((sr) => {
            const def = testCaseSteps?.[sr.step_number - 1]
            return (
              <tr key={sr.id} className="align-top">
                <td className="py-3 pr-3 text-gray-400 tabular-nums">{sr.step_number}</td>
                <td className="py-3 pr-4 text-gray-700 leading-relaxed max-w-[180px]">
                  {def?.action ?? '—'}
                </td>
                <td className="py-3 pr-4 text-gray-500 leading-relaxed max-w-[180px]">
                  {def?.assertion ?? '—'}
                </td>
                <td className="py-3 pr-3">
                  <Badge variant={sr.status}>{sr.status}</Badge>
                </td>
                <td className="py-3 pr-3 text-gray-400 tabular-nums text-center">
                  {sr.retry_count ?? 0}
                </td>
                <td className="py-3 text-gray-500 leading-relaxed max-w-[220px]">
                  {sr.result_reason ?? '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Screenshot grid ───────────────────────────────────────────────────────────

function ScreenshotGrid({ runId }) {
  const [screenshots, setScreenshots] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadScreenshots() {
      setIsLoading(true)
      try {
        const response = await getScreenshots(runId)
        if (!cancelled) {
          setScreenshots(response?.screenshots ?? [])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadScreenshots()

    return () => {
      cancelled = true
    }
  }, [runId])

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="aspect-video rounded-lg bg-gray-100 animate-pulse" />
        ))}
      </div>
    )
  }

  if (!screenshots.length) {
    return <p className="text-xs text-gray-400">No screenshots captured for this run.</p>
  }

  // Group by step number for visual separation
  const byStep = screenshots.reduce((acc, ss) => {
    const k = ss.step_number
    if (!acc[k]) acc[k] = []
    acc[k].push(ss)
    return acc
  }, {})

  return (
    <div className="space-y-5">
      {Object.entries(byStep).map(([stepNum, shots]) => (
        <div key={stepNum}>
          <p className="text-2xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            Step {stepNum}
          </p>
          <div className="flex gap-3 flex-wrap">
            {shots.map((ss) => (
              <div key={ss.id} className="flex flex-col gap-1">
                <a
                  href={screenshotUrl(runId, ss.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-lg overflow-hidden border border-gray-100 hover:border-gray-300 transition-colors"
                  title={`Step ${ss.step_number} — ${ss.kind}`}
                >
                  <img
                    src={screenshotUrl(runId, ss.id)}
                    alt={`Step ${ss.step_number} ${ss.kind}`}
                    className="w-52 h-32 object-cover bg-gray-100"
                    loading="lazy"
                  />
                </a>
                <span className={`text-2xs text-center font-medium ${
                  ss.kind === 'observation' ? 'text-gray-400' : 'text-status-passed-text'
                }`}>
                  {ss.kind}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Log viewer ────────────────────────────────────────────────────────────────

const LOG_LEVELS = ['all']

function logLineClass(line) {
  const l = line.toLowerCase()
  if (l.includes('[error]'))   return 'text-status-failed-text'
  if (l.includes('[warning]')) return 'text-yellow-600'
  if (l.includes('[info]'))    return 'text-gray-500'
  return 'text-gray-400'
}

function matchesLevel(line, level) {
  if (level === 'all') return true
  return line.toLowerCase().includes(`[${level}]`)
}

function LogViewer({ runId }) {
  const [level, setLevel] = useState('all')

  const [rawLines, setRawLines] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadLogs() {
      setIsLoading(true)
      try {
        const response = await getLogs(runId)
        if (!cancelled) {
          setRawLines((response?.logs ?? '').split('\n').filter(Boolean))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadLogs()

    return () => {
      cancelled = true
    }
  }, [runId])

  const lines    = rawLines.filter((l) => matchesLevel(l, level))

  const filterBar = (
    <div className="flex items-center gap-1">
      {LOG_LEVELS.map((l) => (
        <button
          key={l}
          onClick={() => setLevel(l)}
          className={`text-2xs px-2 py-1 rounded transition-colors ${
            level === l
              ? 'bg-gray-900 text-white'
              : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  )

  return (
    <Section title="Logs" action={filterBar}>
      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Spinner size="xs" /> Loading logs…
        </div>
      ) : lines.length === 0 ? (
        <p className="text-xs text-gray-400">
          {rawLines.length > 0 ? 'No lines match the selected filter.' : 'No logs for this run.'}
        </p>
      ) : (
        <pre className="
          font-mono text-xs leading-6 overflow-x-auto
          max-h-96 overflow-y-auto
          rounded-lg bg-gray-50 border border-gray-100 p-4
          whitespace-pre-wrap break-words
        ">
          {lines.map((line, i) => (
            <span key={i} className={`block ${logLineClass(line)}`}>{line}</span>
          ))}
        </pre>
      )}
    </Section>
  )
}

// ── Delete modal ──────────────────────────────────────────────────────────────

function DeleteModal({ open, onClose, onConfirm, loading, error }) {
  return (
    <Modal open={open} onClose={onClose} title="Delete run">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Permanently delete this run and all its screenshots and logs?
          This cannot be undone.
        </p>
        {error && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm} loading={loading}>Delete</Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RunDetailPage() {
  const { runId }      = useParams()
  const navigate       = useNavigate()
  const [showDelete, setShowDelete] = useState(false)
  const [run, setRun] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    let cancelled = false
    let intervalId = null

    async function loadRun() {
      if (!runId) {
        setRun(null)
        setIsLoading(false)
        return
      }

      try {
        const response = await getTestRun(runId)
        if (!cancelled) {
          setRun(response)
          setIsError(false)
          setIsLoading(false)
          if (response?.status === 'running' && intervalId == null) {
            intervalId = window.setInterval(() => {
              getTestRun(runId)
                .then((nextRun) => {
                  if (!cancelled) {
                    setRun(nextRun)
                    if (nextRun?.status !== 'running' && intervalId != null) {
                      window.clearInterval(intervalId)
                      intervalId = null
                    }
                  }
                })
                .catch(() => {
                  if (!cancelled) {
                    setIsError(true)
                  }
                })
            }, 5000)
          }
        }
      } catch {
        if (!cancelled) {
          setIsError(true)
          setIsLoading(false)
          setRun(null)
        }
      }
    }

    setIsLoading(true)
    loadRun()

    return () => {
      cancelled = true
      if (intervalId != null) {
        window.clearInterval(intervalId)
      }
    }
  }, [runId])

  const deleteMutation = useMutation({
    mutationFn: () => deleteTestRun(runId),
    onSuccess: () => {
      navigate(-1)
    },
  })

  // ── Loading / error states ──────────────────────────────────────────────────

  if (isLoading) return <PageSkeleton />

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-sm font-medium text-gray-600">Run not found</p>
          <p className="text-xs text-gray-400">It may have been deleted or the ID is invalid.</p>
          <Button variant="secondary" size="sm" onClick={() => navigate(-1)}>Go back</Button>
        </div>
      </div>
    )
  }

  const totalSteps = (run.steps_passed ?? 0) + (run.steps_failed ?? 0)
  const passRate   = totalSteps > 0 ? Math.round(run.steps_passed / totalSteps * 100) : null

  return (
    <div className="min-h-screen bg-gray-50">

      {/* ── Sticky header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center gap-4">

          {/* Back button */}
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 transition-colors shrink-0"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/>
            </svg>
            Back
          </button>

          <div className="h-4 w-px bg-gray-200 shrink-0" />

          {/* Test case link */}
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <Link
              to={`/projects/${run.project_id}?tc=${run.test_case_id}`}
              className="text-sm font-semibold text-gray-900 hover:text-accent transition-colors truncate"
            >
              {run.test_case_name}
            </Link>
            <span className="text-gray-300 shrink-0">›</span>
            <span className="text-xs text-gray-400 shrink-0 tabular-nums">
              Run {new Date(run.started_at).toLocaleString(undefined, {
                month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </span>
          </div>

          {/* Status + delete */}
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={run.status}>{run.status}</Badge>
            <button
              onClick={() => { deleteMutation.reset(); setShowDelete(true) }}
              className="p-1.5 rounded text-gray-400 hover:text-red-400 hover:bg-red-50 transition-colors"
              aria-label="Delete run"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ───────────────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-8 space-y-5">

        {/* Summary stat boxes */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <StatBox
            label="Status"
            value={run.status}
            valueClass={
              run.status === 'passed' ? 'text-status-passed-text' :
              run.status === 'failed' ? 'text-status-failed-text' :
              run.status === 'running' ? 'text-status-running-text' :
              'text-gray-500'
            }
          />
          <StatBox label="Duration" value={duration(run.duration_seconds)} />
          <StatBox label="Provider"  value={run.provider ?? '—'} />
          <StatBox
            label="Pass rate"
            value={passRate != null ? `${passRate}%` : '—'}
            valueClass={
              parseFloat(passRate) === 100 ? 'text-status-passed-text' :
              passRate != null ? 'text-status-failed-text' :
              'text-gray-400'
            }
          />
          <StatBox
            label="Tokens"
            value={run.total_tokens != null ? run.total_tokens.toLocaleString() : '—'}
          />
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-400 px-1">
          <span>Started: <span className="text-gray-600">{fmt(run.started_at)}</span></span>
          <span>Finished: <span className="text-gray-600">{fmt(run.completed_at)}</span></span>
          {run.model && <span>Model: <span className="text-gray-600">{run.model}</span></span>}
          <span>
            Steps:&nbsp;
            <span className="text-status-passed-text font-medium">{run.steps_passed} passed</span>
            &nbsp;·&nbsp;
            <span className="text-status-failed-text font-medium">{run.steps_failed} failed</span>
          </span>
        </div>

        {/* Step results */}
        <Section title="Step Results">
          <StepResultsTable
            stepResults={run.step_results}
            testCaseSteps={run.steps}
          />
        </Section>

        {/* Screenshots */}
        <Section title="Screenshots">
          <ScreenshotGrid runId={runId} />
        </Section>

        {/* Logs */}
        <LogViewer runId={runId} />

      </main>

      {/* Delete modal */}
      <DeleteModal
        open={showDelete}
        onClose={() => setShowDelete(false)}
        loading={deleteMutation.isPending}
        error={deleteMutation.error?.message}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}
