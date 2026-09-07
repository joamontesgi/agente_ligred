export default function LoadingSpinner({ label = "Cargando..." }) {
  return (
    <div className="loading-spinner" role="status" aria-live="polite">
      <div className="loading-spinner-ring" aria-hidden="true" />
      {label && <p className="loading-spinner-label">{label}</p>}
    </div>
  );
}
