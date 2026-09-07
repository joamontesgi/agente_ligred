import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function LabChat({ sessionId, lab, readOnly, onComplete, onBack }) {
  const [messages, setMessages] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [input, setInput] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const bottomRef = useRef(null);

  const loadSession = async () => {
    const data = await api.getLabSession(sessionId);
    setMessages(data.messages);
    setEvidence(data.evidence || []);
  };

  useEffect(() => {
    if (!sessionId) return;
    loadSession().catch((err) => setError(err.message));
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || readOnly) return;

    setError("");
    setSuccess("");
    setLoading(true);
    const userMsg = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: userMsg },
    ]);

    try {
      const data = await api.sendLabMessage(sessionId, userMsg);
      setMessages((prev) => [...prev, data.message]);
    } catch (err) {
      setError(err.message);
      const data = await api.getLabSession(sessionId).catch(() => null);
      if (data?.messages) {
        setMessages(data.messages);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUploadEvidence = async () => {
    if (evidenceFiles.length === 0) return;

    setError("");
    setSuccess("");
    setUploadingEvidence(true);

    try {
      await api.uploadLabEvidence(sessionId, evidenceFiles, evidenceNote);
      setEvidenceFiles([]);
      setEvidenceNote("");
      setSuccess("Evidencia subida correctamente.");
      await loadSession();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingEvidence(false);
    }
  };

  const handleComplete = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await api.completeLab(sessionId);
      onComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setError("");
    try {
      await api.downloadLabChatPdf(sessionId);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="lab-workspace">
      <aside className="card lab-instructions">
        <div className="row-between">
          <h3>{lab?.title}</h3>
          <button type="button" className="btn-secondary" onClick={onBack}>
            Volver
          </button>
        </div>
        <p className="muted">Tema: {lab?.topic}</p>
        <h4>Instrucciones</h4>
        <pre className="instructions-text">{lab?.instructions}</pre>

        <h4>Evidencia del laboratorio</h4>
        <p className="muted">
          Sube capturas, PDFs o archivos que demuestren que completaste el lab.
        </p>

        <label className="file-input">
          Archivos de evidencia
          <input
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.zip,.doc,.docx"
            onChange={(e) => setEvidenceFiles(Array.from(e.target.files))}
          />
        </label>

        <label>
          Nota (opcional)
          <input
            value={evidenceNote}
            onChange={(e) => setEvidenceNote(e.target.value)}
            placeholder="Ej. Captura del comando ls ejecutado"
          />
        </label>

        {evidenceFiles.length > 0 && (
          <p className="muted">{evidenceFiles.length} archivo(s) seleccionado(s)</p>
        )}

        <button
          type="button"
          className="btn-primary"
          onClick={handleUploadEvidence}
          disabled={uploadingEvidence || evidenceFiles.length === 0}
        >
          Subir evidencia
        </button>

        {evidence.length > 0 && (
          <ul className="list compact evidence-list">
            {evidence.map((item) => (
              <li key={item.id}>{item.filename}</li>
            ))}
          </ul>
        )}

        {!readOnly && (
          <button
            type="button"
            className="btn-primary"
            onClick={handleComplete}
            disabled={loading}
            style={{ marginTop: "1rem" }}
          >
            Finalizar laboratorio
          </button>
        )}
        {readOnly && (
          <p className="badge success" style={{ marginTop: "1rem" }}>
            Laboratorio completado
          </p>
        )}
        <button
          type="button"
          className="btn-secondary"
          onClick={handleDownloadPdf}
          style={{ marginTop: "0.5rem" }}
        >
          Exportar chat PDF
        </button>
      </aside>

      <section className="card lab-chat">
        <h3>Asistente del laboratorio</h3>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}

        <div className="chat-messages">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={msg.role === "user" ? "chat-bubble user" : "chat-bubble assistant"}
            >
              <span className="chat-role">
                {msg.role === "user" ? "Tú" : "Asistente"}
              </span>
              <p>{msg.content}</p>
            </div>
          ))}
          {loading && (
            <div className="chat-bubble assistant">
              <span className="chat-role">Asistente</span>
              <p className="muted">Escribiendo...</p>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {!readOnly && (
          <form onSubmit={handleSend} className="chat-input-row">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu duda sobre el laboratorio..."
              disabled={loading}
            />
            <button type="submit" className="btn-primary" disabled={loading || !input.trim()}>
              Enviar
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
