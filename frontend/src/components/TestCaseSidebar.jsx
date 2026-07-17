

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listTestCases } from '../api/testCases.js'
import Badge   from './ui/Badge.jsx'
import Button  from './ui/Button.jsx'

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SidebarSkeleton() {
  return (
    <div className="space-y-1 p-2 animate-pulse">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-lg px-3 py-2.5 space-y-1.5">
          <div className="h-3 bg-gray-100 rounded w-3/4" />
          <div className="h-2.5 bg-gray-100 rounded w-1/2" />
        </div>
      ))}
    </div>
  )
}

// ── Single test case row ──────────────────────────────────────────────────────

function TestCaseItem({ tc, isActive, isRunning, onSelect }) {
  // Determine the badge to show: running overrides the last run verdict
  const lastStatus = tc.last_run_status ?? null

  return (
    <button
      onClick={() => onSelect(tc.id)}
      className={`
        w-full text-left rounded-lg px-3 py-2.5
        transition-colors duration-100
        ${isActive
          ? 'bg-gray-100 text-gray-900'
          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
        }
      `}
    >
      <div className="flex items-start justify-between gap-1.5">
        <span className={`text-xs leading-snug truncate font-medium ${isActive ? 'text-gray-900' : 'text-gray-700'}`}>
          {tc.name}
        </span>
        {/* Type indicator: P = positive, N = negative */}
        <span className="text-2xs text-gray-300 font-mono shrink-0 mt-px">{tc.type}</span>
      </div>

      <div className="mt-1 flex items-center gap-1.5">
        {isRunning ? (
          <Badge variant="running">running</Badge>
        ) : lastStatus ? (
          <Badge variant={lastStatus}>{lastStatus}</Badge>
        ) : (
          <span className="text-2xs text-gray-300">no runs</span>
        )}
        {tc.runs_count > 0 && (
          <span className="text-2xs text-gray-300">
            {tc.runs_count} {tc.runs_count === 1 ? 'run' : 'runs'}
          </span>
        )}
      </div>
    </button>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function TestCaseSidebar({
  projectId,
  projectName,
  activeId,
  onSelect,
  onNewTestCase,
  runningId = null,
  refreshToken = 0,
}) {
  const navigate = useNavigate()
  const [testCases, setTestCases] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadTestCases() {
      if (!projectId) {
        setTestCases([])
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      try {
        const response = await listTestCases(projectId)
        if (!cancelled) {
          setTestCases(response?.items ?? [])
        }
      } catch {
        if (!cancelled) {
          setTestCases([])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadTestCases()

    return () => {
      cancelled = true
    }
  }, [projectId, refreshToken])

  return (
    <aside className="flex flex-col h-full bg-white border-r border-gray-200 w-64 shrink-0">

      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1 text-2xs text-gray-400 hover:text-gray-600 transition-colors mb-2"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
          Projects
        </button>
        <h2 className="text-sm font-semibold text-gray-900 truncate">{projectName}</h2>
        <p className="text-2xs text-gray-400 mt-0.5">
          {isLoading ? '…' : `${testCases.length} test case${testCases.length !== 1 ? 's' : ''}`}
        </p>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-2">
        {isLoading ? (
          <SidebarSkeleton />
        ) : testCases.length === 0 ? (
          <p className="px-4 py-4 text-2xs text-gray-400 text-center leading-relaxed">
            No test cases yet.<br />Create one below.
          </p>
        ) : (
          <div className="px-2 space-y-0.5">
            {testCases.map((tc) => (
              <TestCaseItem
                key={tc.id}
                tc={tc}
                isActive={tc.id === activeId}
                isRunning={tc.id === runningId}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-gray-100">
        <Button
          variant="secondary"
          size="sm"
          className="w-full justify-center"
          onClick={onNewTestCase}
        >
          + New test case
        </Button>
      </div>
    </aside>
  )
}
