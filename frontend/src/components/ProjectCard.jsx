/**
 * ProjectCard
 *
 * Displays a single project in the grid on the Projects page.
 * Stats (pass rate, total runs) are fetched independently per-card
 * using React Query so each card can show its own loading skeleton
 * without blocking the rest of the grid.
 *
 * Props:
 *   project   ProjectResponse
 *   onEdit    (project) => void
 *   onDelete  (project) => void
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProjectStats } from '../api/projects.js'
import Badge from './ui/Badge.jsx'
import Button from './ui/Button.jsx'

// ── Stat pill (pass rate bar) ─────────────────────────────────────────────────

function PassRateBar({ rate }) {
  // rate is 0–100 from the backend (success_rate field)
  const pct  = (rate ?? 0).toFixed(1)
  const good = pct >= 80
  const warn = pct >= 50 && pct < 80

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-2xs text-gray-400">Pass rate</span>
        <span className={`text-2xs font-semibold ${good ? 'text-status-passed-text' : warn ? 'text-yellow-600' : 'text-status-failed-text'}`}>
          {pct}%
        </span>
      </div>
      <div className="h-1 w-full rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            good ? 'bg-status-passed' : warn ? 'bg-yellow-400' : 'bg-status-failed'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ── Kebab menu ────────────────────────────────────────────────────────────────

function KebabMenu({ onEdit, onDelete }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v) }}
        className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        aria-label="Project options"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
          <circle cx="8" cy="3" r="1.2" />
          <circle cx="8" cy="8" r="1.2" />
          <circle cx="8" cy="13" r="1.2" />
        </svg>
      </button>

      {open && (
        <>
          {/* Invisible overlay to close on outside click */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-7 z-20 w-36 rounded-lg border border-gray-100 bg-white shadow-lg py-1 text-sm">
            <button
              className="w-full text-left px-3 py-1.5 text-gray-700 hover:bg-gray-50 transition-colors"
              onClick={(e) => { e.stopPropagation(); setOpen(false); onEdit() }}
            >
              Edit
            </button>
            <button
              className="w-full text-left px-3 py-1.5 text-red-500 hover:bg-red-50 transition-colors"
              onClick={(e) => { e.stopPropagation(); setOpen(false); onDelete() }}
            >
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// ── Skeleton shown while stats load ──────────────────────────────────────────

function StatsSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="flex justify-between">
        <div className="h-3 w-14 bg-gray-100 rounded" />
        <div className="h-3 w-8 bg-gray-100 rounded" />
      </div>
      <div className="h-1 w-full bg-gray-100 rounded-full" />
      <div className="flex gap-3">
        <div className="h-3 w-16 bg-gray-100 rounded" />
        <div className="h-3 w-16 bg-gray-100 rounded" />
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ProjectCard({ project, onEdit, onDelete }) {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadStats() {
      setStatsLoading(true)
      try {
        const response = await getProjectStats(project.id)
        if (!cancelled) {
          setStats(response)
        }
      } catch {
        if (!cancelled) {
          setStats(null)
        }
      } finally {
        if (!cancelled) {
          setStatsLoading(false)
        }
      }
    }

    loadStats()

    return () => {
      cancelled = true
    }
  }, [project.id])

  const formattedDate = new Date(project.created_at).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })

  return (
    <article
      onClick={() => navigate(`/projects/${project.id}`)}
      className="
        group relative flex flex-col gap-4 rounded-xl border border-gray-200
        bg-white p-5 cursor-pointer
        hover:border-gray-300 hover:shadow-sm
        transition-all duration-150
      "
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate leading-snug">
            {project.name}
          </h3>
          {project.description && (
            <p className="mt-0.5 text-xs text-gray-400 line-clamp-2 leading-relaxed">
              {project.description}
            </p>
          )}
        </div>
        {/* Stop card click from bubbling up through the menu */}
        <div onClick={(e) => e.stopPropagation()}>
          <KebabMenu
            onEdit={() => onEdit(project)}
            onDelete={() => onDelete(project)}
          />
        </div>
      </div>

      {/* Stats section */}
      <div className="flex-1 space-y-3">
        {statsLoading ? (
          <StatsSkeleton />
        ) : stats ? (
          <>
            <PassRateBar rate={stats.success_rate} />
            <div className="flex items-center gap-3 text-2xs text-gray-400">
              <span>
                <span className="font-medium text-gray-600">{stats.total_runs}</span> runs
              </span>
              <span>·</span>
              <span>
                <span className="font-medium text-status-passed-text">{stats.passed_runs}</span> passed
              </span>
              <span>·</span>
              <span>
                <span className="font-medium text-status-failed-text">{stats.failed_runs}</span> failed
              </span>
            </div>
          </>
        ) : null}
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between pt-1 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <Badge variant="neutral">
            {project.test_cases_count} {project.test_cases_count === 1 ? 'test case' : 'test cases'}
          </Badge>
        </div>
        <span className="text-2xs text-gray-400">{formattedDate}</span>
      </div>

      {/* "Open" affordance that appears on hover */}
      <div
        className="
          absolute inset-x-0 bottom-0 flex items-center justify-center
          h-10 rounded-b-xl
          bg-gradient-to-t from-white via-white/80 to-transparent
          opacity-0 group-hover:opacity-100
          transition-opacity duration-150
          pointer-events-none
        "
      >
        <span className="text-xs font-medium text-accent flex items-center gap-1">
          Open workspace
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </div>
    </article>
  )
}
