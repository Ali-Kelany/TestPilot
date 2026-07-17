/**
 * TestCaseForm
 *
 * Shared form used by both the "New test case" and "Edit test case" modals.
 * Handles name, type (P/N), target URL, and a full dynamic steps editor.
 *
 * Props:
 *   initial      Partial<TestCaseResponse>   default values for edit mode
 *   projectId    string                      injected into create payload
 *   onSubmit     (data) => void
 *   loading      boolean
 *   error        string | null
 *   submitLabel  string
 */

import { useState } from 'react'
import StepsList from './StepsList.jsx'
import { Input } from './ui/Input.jsx'
import Button from './ui/Button.jsx'

const EMPTY_STEP = { action: '', assertion: '' }

export default function TestCaseForm({
  initial = {},
  projectId,
  onSubmit,
  loading,
  error,
  submitLabel = 'Save',
}) {
  const [name,    setName]    = useState(initial.name       ?? '')
  const [type,    setType]    = useState(initial.type       ?? 'P')
  const [url,     setUrl]     = useState(initial.target_url ?? '')
  const [steps,   setSteps]   = useState(initial.steps?.length ? initial.steps : [EMPTY_STEP])

  // Per-field validation errors
  const [errors, setErrors] = useState({})

  const validate = () => {
    const e = {}
    if (!name.trim())  e.name = 'Name is required'
    if (!url.trim())   e.url  = 'Target URL is required'
    const badSteps = steps.some((s) => !s.action.trim() || !s.assertion.trim())
    if (badSteps)      e.steps = 'Every step needs an action and an assertion'
    return e
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }

    onSubmit({
      project_id:  projectId,
      name:        name.trim(),
      type,
      target_url:  url.trim(),
      steps:       steps.map((s) => ({ action: s.action.trim(), assertion: s.assertion.trim() })),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* Name + type row */}
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <Input
            label="Name"
            placeholder="e.g. Guest checkout"
            value={name}
            onChange={(e) => { setName(e.target.value); setErrors((v) => ({ ...v, name: null })) }}
            error={errors.name}
            autoFocus
          />
        </div>

        {/* P / N toggle */}
        <div className="shrink-0 pb-px">
          <p className="text-xs font-medium text-gray-600 mb-1">Type</p>
          <div className="flex rounded-md border border-gray-200 overflow-hidden text-xs font-medium">
            {['P', 'N'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={`
                  px-3 py-2 leading-none transition-colors
                  ${type === t
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-500 hover:bg-gray-50'
                  }
                `}
                title={t === 'P' ? 'Positive test' : 'Negative test'}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Target URL */}
      <Input
        label="Target URL"
        type="url"
        placeholder="https://example.com/page"
        value={url}
        onChange={(e) => { setUrl(e.target.value); setErrors((v) => ({ ...v, url: null })) }}
        error={errors.url}
      />

      {/* Steps */}
      <div>
        <p className="text-xs font-medium text-gray-600 mb-2">Steps</p>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
          <StepsList
            steps={steps}
            editing
            onChange={(updated) => {
              setSteps(updated)
              setErrors((v) => ({ ...v, steps: null }))
            }}
          />
        </div>
        {errors.steps && (
          <p className="mt-1 text-xs text-red-500">{errors.steps}</p>
        )}
      </div>

      {/* Server error */}
      {error && (
        <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-1">
        <Button type="submit" variant="primary" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
