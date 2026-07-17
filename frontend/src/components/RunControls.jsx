/**
 * RunControls
 *
 * The strip of controls above the run history / live panel.
 * Manages provider selection and headless toggle locally;
 * exposes run config upward via onRun().
 *
 * Props:
 *   isRunning   boolean          — a run is currently active
 *   onRun       (config) => void — called with { provider, headless }
 *   onStop      () => void       — close the WebSocket
 *   disabled    boolean          — disable the whole strip (e.g. while saving)
 */

import useLocalStorage from '../hooks/useLocalStorage.js'
import Button from './ui/Button.jsx'

const PROVIDERS = ['ollama', 'mistral', 'google', 'openrouter', 'llama_cpp']

export default function RunControls({ isRunning, onRun, onStop, disabled = false }) {
  const [provider, setProvider] = useLocalStorage('run_provider', 'google')
  const [models, setModels] = useLocalStorage('run_models', {
    ollama: 'gemma4:31b-cloud',
    mistral: 'mistral-large-2512',
    google: 'gemma-4-31b-it',
    openrouter: 'sourceful/riverflow-v2-pro',
    llama_cpp: '',
  })
  const [headless, setHeadless] = useLocalStorage('run_headless', true)

  const currentModel = models[provider] ?? ''

  const handleRun = () => {
    if (isRunning) { onStop(); return }
    onRun({ provider, model: provider === 'llama_cpp' ? null : (currentModel || null), headless })
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">

      {/* Provider */}
      <div className="flex items-center gap-1.5">
        <label className="text-2xs text-gray-400 font-medium shrink-0">Provider</label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          disabled={isRunning || disabled}
          className="
            text-xs rounded-md border border-gray-200 bg-white
            px-2 py-1.5 text-gray-700 outline-none
            focus:border-accent focus:ring-1 focus:ring-accent
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Model */}
      <div className="flex items-center gap-1.5">
        <label className="text-2xs text-gray-400 font-medium shrink-0">Model</label>
        <input
          type="text"
          value={provider === 'llama_cpp' ? '' : currentModel}
          onChange={(e) => setModels({ ...models, [provider]: e.target.value })}
          placeholder="e.g. mistral-large"
          disabled={provider === 'llama_cpp' || isRunning || disabled}
          className="
            text-xs rounded-md border border-gray-200 bg-white
            px-2 py-1.5 text-gray-700 outline-none w-40
            focus:border-accent focus:ring-1 focus:ring-accent
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors placeholder:text-gray-300
          "
        />
      </div>

      {/* Headless toggle */}
      <button
        type="button"
        onClick={() => setHeadless((v) => !v)}
        disabled={isRunning || disabled}
        className="flex items-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
        aria-pressed={headless}
        aria-label="Toggle headless mode"
      >
        {/* Track */}
        <span
          className={`
            relative inline-flex h-4 w-7 shrink-0 rounded-full border-2 border-transparent
            transition-colors duration-200 cursor-pointer
            ${headless ? 'bg-accent' : 'bg-gray-200'}
          `}
        >
          {/* Thumb */}
          <span
            className={`
              pointer-events-none inline-block h-3 w-3 rounded-full bg-white shadow
              transition-transform duration-200
              ${headless ? 'translate-x-3' : 'translate-x-0'}
            `}
          />
        </span>
        <span className="text-xs text-gray-500 group-hover:text-gray-700 transition-colors">
          Headless
        </span>
      </button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Run / Stop */}
      <Button
        variant={isRunning ? 'danger' : 'primary'}
        size="sm"
        onClick={handleRun}
        disabled={disabled}
        className="min-w-[80px]"
      >
        {isRunning ? (
          <>
            <span className="inline-block w-2 h-2 bg-current rounded-sm" />
            Stop
          </>
        ) : (
          <>
            {/* Play triangle */}
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M3 2.5v11l10-5.5L3 2.5z"/>
            </svg>
            Run
          </>
        )}
      </Button>
    </div>
  )
}
