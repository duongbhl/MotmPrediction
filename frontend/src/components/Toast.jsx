const TYPE_STYLES = {
  success: 'border-green bg-green/10 text-green',
  error:   'border-red  bg-red/10  text-red',
  info:    'border-blue bg-blue/10 text-text',
}

export default function Toast({ type, msg }) {
  const cls = TYPE_STYLES[type] || TYPE_STYLES.info
  return (
    <div
      className={`fixed bottom-6 right-6 z-[1000] flex items-center gap-2.5 px-5 py-3.5 rounded-[12px] border text-sm font-semibold max-w-[340px] [animation:toastIn_0.35s_cubic-bezier(0.34,1.56,0.64,1)_forwards] ${cls}`}
    >
      <span>{type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
      <span>{msg}</span>
    </div>
  )
}

