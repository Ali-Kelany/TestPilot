
import Spinner from './Spinner.jsx'

const base = `
  inline-flex items-center justify-center gap-1.5 rounded-md
  font-medium leading-none transition-colors
  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
  disabled:pointer-events-none disabled:opacity-50
`

const variants = {
  primary:   'bg-accent text-white hover:bg-accent-hover',
  secondary: 'border border-gray-200 bg-white text-gray-700 hover:bg-gray-50',
  ghost:     'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
  danger:    'border border-red-200 text-red-600 bg-white hover:bg-red-50',
}

const sizes = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-3.5 py-2 text-sm',
}

export default function Button({
  variant  = 'secondary',
  size     = 'md',
  loading  = false,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  return (
    <button
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {loading && <Spinner size="xs" />}
      {children}
    </button>
  )
}
