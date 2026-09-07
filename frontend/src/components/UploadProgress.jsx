export default function UploadProgress({ progress }) {
  if (!progress?.active) return null;

  const { current, total, filename, percent, status } = progress;

  let label = "Procesando documentos...";
  if (filename) {
    if (status === "processing") {
      label = `Indexando ${filename} (${current} de ${total})...`;
    } else {
      label = `Subiendo ${current} de ${total}: ${filename}`;
    }
  }

  return (
    <div className="upload-progress" role="status" aria-live="polite">
      <div className="upload-progress-header">
        <span>{label}</span>
        <span>{percent}%</span>
      </div>
      <div className="upload-progress-track">
        <div
          className={`upload-progress-bar${status === "processing" ? " processing" : ""}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
