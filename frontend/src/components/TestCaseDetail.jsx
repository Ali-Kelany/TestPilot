

import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  getTestCase,
  updateTestCase,
  deleteTestCase,
} from '../api/testCases.js'
import StepsList     from './StepsList.jsx'
import RunControls   from './RunControls.jsx'
import RunHistory    from './RunHistory.jsx'
import LiveRunPanel  from './LiveRunPanel.jsx'
import TestCaseForm  from './TestCaseForm.jsx'
import Modal         from './ui/Modal.jsx'
import Button        from './ui/Button.jsx'
import Badge         from './ui/Badge.jsx'

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="space-y-2">
        <div className="h-5 w-1/3 bg-gray-100 rounded" />
        <div className="h-3 w-1/2 bg-gray-100 rounded" />
      </div>
      <div className="space-y-2.5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-5 w-5 rounded-full bg-gray-100 shrink-0" />
            <div className="flex-1 grid grid-cols-2 gap-4">
              <div className="h-3 bg-gray-100 rounded" />
              <div className="h-3 bg-gray-100 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Kebab menu (edit / delete) ────────────────────────────────────────────────

function ActionMenu({ onEdit, onDelete }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-label="Test case options"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
          <circle cx="8" cy="3" r="1.2"/>
          <circle cx="8" cy="8" r="1.2"/>
          <circle cx="8" cy="13" r="1.2"/>
        </svg>
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-8 z-20 w-36 rounded-lg border border-gray-100 bg-white shadow-lg py-1 text-sm">
            <button
              className="w-full text-left px-3 py-1.5 text-gray-700 hover:bg-gray-50 transition-colors text-xs"
              onClick={() => { setOpen(false); onEdit() }}
            >
              Edit
            </button>
            <button
              className="w-full text-left px-3 py-1.5 text-red-500 hover:bg-red-50 transition-colors text-xs"
              onClick={() => { setOpen(false); onDelete() }}
            >
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ label, children, className = '' }) {
  return (
    <div className={`px-6 py-4 border-b border-gray-100 last:border-0 ${className}`}>
      {label && (
        <p className="text-2xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          {label}
        </p>
      )}
      {children}
    </div>
  )
}

// ── Delete confirmation modal ─────────────────────────────────────────────────

function DeleteModal({ name, onConfirm, onClose, loading, error }) {
  return (
    <Modal open title="Delete test case" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Delete <span className="font-semibold text-gray-900">{name}</span>?
          All run history and screenshots will be permanently removed.
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

// ── Main ──────────────────────────────────────────────────────────────────────

export default function TestCaseDetail({
  testCaseId,
  projectId,
  isRunning,
  events,
  sessionId,
  onRun,
  onStop,
  onDeleted,
  refreshToken = 0,
  onRefresh,
}) {
  const [showEdit,   setShowEdit]   = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [tc, setTc] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadTestCase() {
      if (!testCaseId) {
        setTc(null)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setIsError(false)
      try {
        const response = await getTestCase(testCaseId)
        if (!cancelled) {
          setTc(response)
        }
      } catch {
        if (!cancelled) {
          setIsError(true)
          setTc(null)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadTestCase()

    return () => {
      cancelled = true
    }
  }, [testCaseId, refreshToken])

  // Edit mutation
  const editMutation = useMutation({
    mutationFn: (data) => updateTestCase(testCaseId, data),
    onSuccess: (updated) => {
      setTc(updated)
      onRefresh?.()
      setShowEdit(false)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteTestCase(testCaseId),
    onSuccess: () => {
      onRefresh?.()
      setShowDelete(false)
      onDeleted?.()
    },
  })

  // ── Render states ──────────────────────────────────────────────────────────

  if (isLoading) return <DetailSkeleton />

  if (isError) {
    return (
      <div className="p-6 text-xs text-red-400">
        Failed to load test case.
      </div>
    )
  }

  if (!tc) return null

  return (
    <>
      <div className="flex flex-col h-full overflow-y-auto">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5 flex-wrap">
              <h2 className="text-sm font-semibold text-gray-900">{tc.name}</h2>
              <Badge variant={tc.type === 'N' ? 'neutral' : 'accent'}>
                {tc.type === 'P' ? 'Positive' : 'Negative'}
              </Badge>
            </div>
            <a
              href={tc.target_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-blue-500 hover:underline truncate block max-w-sm"
              onClick={(e) => e.stopPropagation()}
            >
              {tc.target_url}
            </a>
            <p className="text-2xs text-gray-400 mt-1">
              {tc.runs_count} {tc.runs_count === 1 ? 'run' : 'runs'} total
            </p>
          </div>

          <ActionMenu
            onEdit={() => { editMutation.reset(); setShowEdit(true) }}
            onDelete={() => { deleteMutation.reset(); setShowDelete(true) }}
          />
        </div>

        {/* ── Steps ───────────────────────────────────────────────────────── */}
        <Section label="Steps">
          <StepsList steps={tc.steps} editing={false} />
        </Section>

        {/* ── Run controls ────────────────────────────────────────────────── */}
        <Section label="Execute">
          <RunControls
            isRunning={isRunning}
            onRun={onRun}
            onStop={onStop}
          />
        </Section>

        {/* ── Body: history or live panel ──────────────────────────────────── */}
        <Section label={isRunning ? 'Live run' : 'Run history'} className="flex-1">
          {isRunning
              ? <LiveRunPanel events={events ?? []} sessionId={sessionId} onStop={onStop} />
              : <RunHistory testCaseId={testCaseId} refreshToken={refreshToken} />
          }
        </Section>
      </div>

      {/* ── Edit modal ──────────────────────────────────────────────────────── */}
      {showEdit && (
        <Modal open onClose={() => setShowEdit(false)} title="Edit test case" className="max-w-7xl">
          <TestCaseForm
            key={tc.id}
            initial={tc}
            projectId={projectId}
            submitLabel="Save changes"
            loading={editMutation.isPending}
            error={editMutation.error?.message}
            onSubmit={(data) => editMutation.mutate(data)}
          />
        </Modal>
      )}

      {/* ── Delete modal ────────────────────────────────────────────────────── */}
      {showDelete && (
        <DeleteModal
          name={tc.name}
          onClose={() => setShowDelete(false)}
          loading={deleteMutation.isPending}
          error={deleteMutation.error?.message}
          onConfirm={() => deleteMutation.mutate()}
        />
      )}
    </>
  )
}
