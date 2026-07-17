/**
 * StepsList
 *
 * Renders the steps array of a test case in two modes:
 *
 *  read  — numbered rows, action + assertion, no interaction
 *  edit  — each row becomes two text inputs; rows can be added / removed / reordered
 *
 * Props:
 *   steps      { action: string, assertion: string }[]
 *   editing    boolean
 *   onChange   (steps) => void   — called on every change in edit mode
 */

import { useEffect, useState } from 'react'
import Button from './ui/Button.jsx'

// ── Single editable row ───────────────────────────────────────────────────────

function EditRow({ index, step, total, onChange, onRemove, onMove }) {
  return (
    <div className="group flex gap-2 items-start">

      {/* Step number + reorder buttons */}
      <div className="flex flex-col items-center gap-0.5 pt-2 shrink-0">
        <span className="text-2xs font-medium text-gray-400 w-5 text-center tabular-nums">
          {index + 1}
        </span>
        <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            disabled={index === 0}
            onClick={() => onMove(index, -1)}
            className="text-gray-300 hover:text-gray-500 disabled:opacity-20 leading-none"
            aria-label="Move step up"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 4l4 5H4l4-5z"/>
            </svg>
          </button>
          <button
            type="button"
            disabled={index === total - 1}
            onClick={() => onMove(index, 1)}
            className="text-gray-300 hover:text-gray-500 disabled:opacity-20 leading-none"
            aria-label="Move step down"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 12L4 7h8l-4 5z"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Inputs */}
      <div className="flex-1 grid grid-cols-2 gap-2">
        <div>
          <label className="block text-2xs text-gray-400 mb-1">Action</label>
          <textarea
            rows={3}
            value={step.action}
            onChange={(e) => onChange(index, 'action', e.target.value)}
            placeholder="What the agent does…"
            className="
              w-full rounded border border-gray-200 px-2.5 py-1.5
              text-xs text-gray-900 placeholder-gray-300
              resize-none outline-none
              focus:border-accent focus:ring-1 focus:ring-accent
              transition-colors
            "
          />
        </div>
        <div>
          <label className="block text-2xs text-gray-400 mb-1">Assertion</label>
          <textarea
            rows={3}
            value={step.assertion}
            onChange={(e) => onChange(index, 'assertion', e.target.value)}
            placeholder="What to verify…"
            className="
              w-full rounded border border-gray-200 px-2.5 py-1.5
              text-xs text-gray-900 placeholder-gray-300
              resize-none outline-none
              focus:border-accent focus:ring-1 focus:ring-accent
              transition-colors
            "
          />
        </div>
      </div>

      {/* Remove */}
      <button
        type="button"
        onClick={() => onRemove(index)}
        disabled={total <= 1}
        className="mt-2 p-1 text-gray-300 hover:text-red-400 disabled:opacity-20 transition-colors shrink-0"
        aria-label="Remove step"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  )
}

// ── Read-only row ─────────────────────────────────────────────────────────────

function ReadRow({ index, step }) {
  return (
    <div className="flex gap-3 items-start">
      <span className="
        mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center
        rounded-full border border-gray-200
        text-2xs font-medium text-gray-400 tabular-nums
      ">
        {index + 1}
      </span>
      <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
        <p className="text-xs text-gray-800 leading-relaxed">{step.action}</p>
        <p className="text-xs text-gray-500 leading-relaxed">{step.assertion}</p>
      </div>
    </div>
  )
}

// ── Column headers (shown in both modes) ──────────────────────────────────────

function ColumnHeaders({ editing }) {
  return (
    <div className={`grid grid-cols-2 gap-x-4 text-2xs font-medium text-gray-400 uppercase tracking-wide ${editing ? 'ml-7 mr-7' : 'ml-8'}`}>
      <span>Action</span>
      <span>Assertion</span>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function StepsList({ steps, editing = false, onChange }) {
  // Local draft — synced from props when editing starts
  const [draft, setDraft] = useState(steps)
  useEffect(() => { setDraft(steps) }, [steps, editing])

  const update = (updated) => {
    setDraft(updated)
    onChange?.(updated)
  }

  const handleChange = (idx, field, value) => {
    const next = draft.map((s, i) => i === idx ? { ...s, [field]: value } : s)
    update(next)
  }

  const handleRemove = (idx) => {
    update(draft.filter((_, i) => i !== idx))
  }

  const handleMove = (idx, dir) => {
    const next = [...draft]
    const swap = idx + dir
    ;[next[idx], next[swap]] = [next[swap], next[idx]]
    update(next)
  }

  const handleAdd = () => {
    update([...draft, { action: '', assertion: '' }])
  }

  if (!steps?.length && !editing) {
    return <p className="text-xs text-gray-400 py-2">No steps defined.</p>
  }

  return (
    <div className="space-y-3">
      <ColumnHeaders editing={editing} />

      <div className="space-y-2.5">
        {(editing ? draft : steps).map((step, i) =>
          editing ? (
            <EditRow
              key={i}
              index={i}
              step={step}
              total={draft.length}
              onChange={handleChange}
              onRemove={handleRemove}
              onMove={handleMove}
            />
          ) : (
            <ReadRow key={i} index={i} step={step} />
          )
        )}
      </div>

      {editing && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleAdd}
          className="text-accent hover:text-accent-hover"
        >
          + Add step
        </Button>
      )}
    </div>
  )
}
