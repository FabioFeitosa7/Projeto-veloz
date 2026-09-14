export default function StatusMessage({ tipo = 'info', children, onRetry }) {
  return (
    <div className={`status-message status-${tipo}`} role={tipo === 'erro' ? 'alert' : 'status'}>
      <p>{children}</p>
      {onRetry && <button type="button" onClick={onRetry}>Tentar novamente</button>}
    </div>
  )
}
