import { useEffect, useState } from "react";
import { api } from "../api/client";
import Pagination from "./Pagination";
import UploadProgress from "./UploadProgress";
import { usePagination } from "../hooks/usePagination";
import { confirmAction } from "../utils/swal";

export default function TeacherWordCloud({ subjects, selectedSubjectId, onSubjectChange }) {
  const [pdfs, setPdfs] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedPdfIds, setSelectedPdfIds] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  const isUploading = Boolean(uploadProgress?.active);
  const pdfsPagination = usePagination(pdfs, 5);
  const topTermsPagination = usePagination(analysis?.top_terms || [], 10);

  const loadPdfs = async (subjectId) => {
    if (!subjectId) return;
    const data = await api.getConversationPdfs(subjectId);
    setPdfs(data.pdfs);
    setSelectedPdfIds(data.pdfs.map((pdf) => pdf.id));
  };

  useEffect(() => {
    if (!selectedSubjectId) return;
    setAnalysis(null);
    setError("");
    loadPdfs(selectedSubjectId).catch((err) => setError(err.message));
  }, [selectedSubjectId]);

  const togglePdfSelection = (pdfId) => {
    setSelectedPdfIds((current) =>
      current.includes(pdfId)
        ? current.filter((id) => id !== pdfId)
        : [...current, pdfId],
    );
  };

  const handleUpload = async () => {
    if (!selectedSubjectId || files.length === 0) return;

    setError("");
    setMessage("");
    setLoading(true);
    setUploadProgress({
      active: true,
      current: 0,
      total: files.length,
      filename: "",
      percent: 0,
      status: "uploading",
    });

    try {
      const data = await api.uploadConversationPdfs(
        selectedSubjectId,
        files,
        (progress) => setUploadProgress({ active: true, ...progress }),
      );
      const okCount = data.results.filter((result) => result.ok).length;
      setMessage(`${okCount} PDF(s) de conversación cargado(s).`);
      setFiles([]);
      await loadPdfs(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadProgress(null);
      setLoading(false);
    }
  };

  const handleDelete = async (pdfId, filename) => {
    const confirmed = await confirmAction({
      title: "Eliminar PDF",
      text: `¿Eliminar «${filename}» de la nube de palabras?`,
      confirmText: "Eliminar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    try {
      await api.deleteConversationPdf(pdfId);
      setMessage("PDF eliminado.");
      await loadPdfs(selectedSubjectId);
      setAnalysis(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGenerate = async () => {
    if (!selectedSubjectId || selectedPdfIds.length === 0) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const data = await api.generateWordCloud(selectedSubjectId, selectedPdfIds);
      setAnalysis(data);
      setMessage(
        `Nube generada con ${data.documents_used} documento(s) y ${data.total_words} palabras analizadas.`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (subjects.length === 0) {
    return (
      <section className="card">
        <h3>Nube de palabras</h3>
        <p className="muted">Primero crea una asignatura.</p>
      </section>
    );
  }

  return (
    <div className="grid-2">
      <section className="card">
        <h3>Nube de palabras</h3>
        <p className="muted">
          Sube PDFs exportados de conversaciones (por ejemplo, chats de laboratorio) y
          genera una nube con los términos más frecuentes.
        </p>

        {message && <p className="success">{message}</p>}
        {error && <p className="error">{error}</p>}

        <label>
          Asignatura
          <select
            value={selectedSubjectId || ""}
            onChange={(event) => onSubjectChange(Number(event.target.value))}
          >
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </label>

        <label className="file-input">
          PDFs de conversaciones
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={(event) => setFiles(Array.from(event.target.files))}
          />
        </label>

        {files.length > 0 && (
          <p className="muted">{files.length} archivo(s) seleccionado(s)</p>
        )}

        <UploadProgress progress={uploadProgress} />

        <button
          type="button"
          className="btn-primary"
          onClick={handleUpload}
          disabled={loading || isUploading || files.length === 0}
        >
          {isUploading ? "Subiendo..." : "Cargar PDFs"}
        </button>

        <h4>PDFs cargados</h4>
        {pdfs.length === 0 ? (
          <p className="muted">No hay PDFs de conversación para esta asignatura.</p>
        ) : (
          <>
          <ul className="list compact">
            {pdfsPagination.pageItems.map((pdf) => (
              <li key={pdf.id} className="wordcloud-pdf-item">
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={selectedPdfIds.includes(pdf.id)}
                    onChange={() => togglePdfSelection(pdf.id)}
                  />
                  <span>
                    {pdf.filename}
                    {pdf.uploaded_at && (
                      <small className="muted">
                        {" "}
                        — {new Date(pdf.uploaded_at).toLocaleString()}
                      </small>
                    )}
                  </span>
                </label>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => handleDelete(pdf.id, pdf.filename)}
                >
                  Eliminar
                </button>
              </li>
            ))}
          </ul>
          <Pagination
            page={pdfsPagination.page}
            totalPages={pdfsPagination.totalPages}
            totalItems={pdfsPagination.totalItems}
            pageSize={pdfsPagination.pageSize}
            onPageChange={pdfsPagination.setPage}
          />
          </>
        )}

        <button
          type="button"
          className="btn-primary"
          onClick={handleGenerate}
          disabled={loading || selectedPdfIds.length === 0}
        >
          {loading && !isUploading ? "Generando..." : "Generar nube de palabras"}
        </button>
      </section>

      <section className="card">
        <h3>Resultado</h3>
        {!analysis ? (
          <p className="muted">
            Selecciona uno o más PDFs y pulsa &quot;Generar nube de palabras&quot;.
          </p>
        ) : (
          <>
            <div className="metrics-grid">
              <div className="metric-card">
                <span>Documentos</span>
                <strong>{analysis.documents_used}</strong>
              </div>
              <div className="metric-card">
                <span>Palabras analizadas</span>
                <strong>{analysis.total_words}</strong>
              </div>
              <div className="metric-card">
                <span>Términos únicos</span>
                <strong>{analysis.unique_words}</strong>
              </div>
            </div>

            <div className="wordcloud-image-wrap">
              <img
                src={`data:image/png;base64,${analysis.image_base64}`}
                alt="Nube de palabras generada"
                className="wordcloud-image"
              />
            </div>

            <h4>Términos más frecuentes</h4>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Término</th>
                    <th>Frecuencia</th>
                  </tr>
                </thead>
                <tbody>
                  {topTermsPagination.pageItems.map((item) => (
                    <tr key={item.word}>
                      <td>{item.word}</td>
                      <td>{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={topTermsPagination.page}
              totalPages={topTermsPagination.totalPages}
              totalItems={topTermsPagination.totalItems}
              pageSize={topTermsPagination.pageSize}
              onPageChange={topTermsPagination.setPage}
            />
          </>
        )}
      </section>
    </div>
  );
}
