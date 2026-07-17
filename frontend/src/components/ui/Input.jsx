export function Input({ label, error, className = '', ...rest }) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs font-medium text-gray-600 mb-1">{label}</span>
      )}
      <input
        className={`
          block w-full rounded-md border px-3 py-2 text-sm text-gray-900
          placeholder-gray-400 outline-none transition-colors
          border-gray-200 bg-white
          focus:border-accent focus:ring-1 focus:ring-accent
          disabled:bg-gray-50 disabled:text-gray-400
          ${error ? 'border-red-400 focus:border-red-400 focus:ring-red-400' : ''}
          ${className}
        `}
        {...rest}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </label>
  )
}

export function Textarea({ label, error, className = '', ...rest }) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs font-medium text-gray-600 mb-1">{label}</span>
      )}
      <textarea
        rows={3}
        className={`
          block w-full rounded-md border px-3 py-2 text-sm text-gray-900
          placeholder-gray-400 outline-none transition-colors resize-none
          border-gray-200 bg-white
          focus:border-accent focus:ring-1 focus:ring-accent
          ${error ? 'border-red-400 focus:border-red-400 focus:ring-red-400' : ''}
          ${className}
        `}
        {...rest}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </label>
  )
}
