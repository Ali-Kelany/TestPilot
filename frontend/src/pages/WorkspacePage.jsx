
import { useState, useCallback, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { getProject } from '../api/projects.js'
import { createTestCase, stopTestCase } from '../api/testCases.js'
import { useRunWebSocket } from '../hooks/useRunWebSocket.js'
import TestCaseSidebar from '../components/TestCaseSidebar.jsx'
import TestCaseDetail  from '../components/TestCaseDetail.jsx'
import TestCaseForm    from '../components/TestCaseForm.jsx'
import Modal           from '../components/ui/Modal.jsx'

// ── No-selection placeholder ──────────────────────────────────────────────────

function EmptyDetail() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-500 mb-1">Select a test case</p>
      <p className="text-xs text-gray-400 max-w-xs leading-relaxed">
        Choose a test case from the sidebar to view its steps, run history, and controls.
      </p>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const { projectId }                  = useParams()
  const [searchParams, setSearchParams] = useSearchParams()

  // Selected test case id lives in ?tc= param
  const activeId = searchParams.get('tc') ?? null
  const [project, setProject] = useState(null)
  const [refreshTick, setRefreshTick] = useState(0)

  const refreshWorkspace = useCallback(() => {
    setRefreshTick((tick) => tick + 1)
  }, [])

  const selectTestCase = useCallback((id) => {
    setSearchParams(id ? { tc: id } : {}, { replace: true })
  }, [setSearchParams])

  // ── Project meta (for sidebar header) ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false

    async function loadProject() {
      if (!projectId) {
        setProject(null)
        return
      }

      try {
        const response = await getProject(projectId)
        if (!cancelled) {
          setProject(response)
        }
      } catch {
        if (!cancelled) {
          setProject(null)
        }
      }
    }

    loadProject()

    return () => {
      cancelled = true
    }
  }, [projectId, refreshTick])

  // ── New test case modal ─────────────────────────────────────────────────────
  const [showCreate, setShowCreate] = useState(false)

  const createMutation = useMutation({
    mutationFn: createTestCase,
    onSuccess: (created) => {
      refreshWorkspace()
      setShowCreate(false)
      selectTestCase(created.id)   // auto-select the newly created test case
    },
  })

  // ── WebSocket run state ─────────────────────────────────────────────────────
  // runningTcId tracks which test case triggered the active run so the
  // sidebar can highlight it and TestCaseDetail can swap in the live panel.
  const [runningTcId, setRunningTcId] = useState(null)

  const handleFinished = useCallback(() => {
    setRunningTcId(null)
    refreshWorkspace()
  }, [refreshWorkspace])

  const { isRunning, events, sessionId, startRun, stopWatching } = useRunWebSocket(
    activeId ?? '__none__',   // hook always needs a string; '__none__' is never connected
    handleFinished,
  )

  const handleRun = useCallback((config) => {
    setRunningTcId(activeId)
    startRun(config)
  }, [activeId, startRun])

  const handleStop = useCallback(() => {
    stopWatching()
    const tcId = runningTcId
    if (tcId) {
      stopTestCase(tcId).catch(console.error)
    }
    setRunningTcId(null)
    refreshWorkspace()
  }, [stopWatching, runningTcId, refreshWorkspace])

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">

      {/* Sidebar */}
      <TestCaseSidebar
        projectId={projectId}
        projectName={project?.name ?? '…'}
        activeId={activeId}
        onSelect={selectTestCase}
        onNewTestCase={() => { createMutation.reset(); setShowCreate(true) }}
        runningId={runningTcId}
        refreshToken={refreshTick}
      />

      {/* Main panel */}
      <main className="flex-1 overflow-hidden bg-white">
        {activeId ? (
          <TestCaseDetail
            key={activeId}           /* remount when switching test cases */
            testCaseId={activeId}
            projectId={projectId}
            isRunning={isRunning && runningTcId === activeId}
            events={events}
            sessionId={sessionId}
            onRun={handleRun}
            onStop={handleStop}
            onDeleted={() => selectTestCase(null)}
            refreshToken={refreshTick}
            onRefresh={refreshWorkspace}
          />
        ) : (
          <EmptyDetail />
        )}
      </main>

      {/* New test case modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="New test case"
        className="max-w-7xl"
      >
        <TestCaseForm
          projectId={projectId}
          submitLabel="Create test case"
          loading={createMutation.isPending}
          error={createMutation.error?.message}
          onSubmit={(data) => createMutation.mutate(data)}
        />
      </Modal>
    </div>
  )
}
