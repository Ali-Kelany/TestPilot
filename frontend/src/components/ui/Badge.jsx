import Spinner from './Spinner.jsx'

const variants = {
  passed:  'bg-status-passed-bg  text-status-passed-text',
  failed:  'bg-status-failed-bg  text-status-failed-text',
  error:   'bg-status-error-bg   text-status-error-text',
  running: 'bg-status-running-bg text-status-running-text',
  aborted: 'bg-status-aborted-bg text-status-aborted-text',
  neutral: 'bg-gray-100          text-gray-500',
  accent:  'bg-accent-subtle     text-accent-text',
}

export default function Badge({ variant = 'neutral', dot = false, className = '', children }) {
  const isRunning = variant === 'running'

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded px-1.5 py-0.5
        text-2xs font-medium leading-none whitespace-nowrap
        ${variants[variant] ?? variants.neutral}
        ${className}
      `}
    >
      {/* Animated spinner for running, static dot for others when dot=true */}
      {isRunning && <Spinner size="xs" />}
      {!isRunning && dot && (
        <span className="block w-1.5 h-1.5 rounded-full bg-current opacity-70" />
      )}
      {children}
    </span>
  )
}
