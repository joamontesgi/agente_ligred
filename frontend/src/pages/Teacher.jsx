import { useEffect, useState } from "react";
import { api } from "../api/client";
import Pagination from "../components/Pagination";
import ResponsiveNav from "../components/ResponsiveNav";
import TeacherMetrics from "../components/TeacherMetrics";
import TeacherWordCloud from "../components/TeacherWordCloud";
import UploadProgress from "../components/UploadProgress";
import { usePagination } from "../hooks/usePagination";
import { formatSubjectTeachers } from "../utils/subjectTeachers";
import { confirmAction } from "../utils/swal";

const TEACHER_TABS = [
  { id: "subjects", label: "Asignaturas" },
  { id: "documents", label: "Documentos" },
  { id: "evaluations", label: "Evaluaciones" },
  { id: "labs", label: "Laboratorios" },
  { id: "metrics", label: "Métricas" },
  { id: "wordcloud", label: "Nube de palabras" },
];

export default function Teacher() {
  const [tab, setTab] = useState("subjects");
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [labs, setLabs] = useState([]);
  const [labSessions, setLabSessions] = useState([]);
  const [selectedLab, setSelectedLab] = useState(null);
  const [selectedLabId, setSelectedLabId] = useState(null);
  const [labDocuments, setLabDocuments] = useState([]);
  const [labFiles, setLabFiles] = useState([]);
  const [viewingSession, setViewingSession] = useState(null);
  const [sessionChat, setSessionChat] = useState(null);
  const [newLab, setNewLab] = useState({ title: "", topic: "", instructions: "" });
  const [files, setFiles] = useState([]);
  const [newSubject, setNewSubject] = useState({
    name: "",
    description: "",
    llm_model: "",
  });
  const [ollamaModels, setOllamaModels] = useState([]);
  const [llamaModels, setLlamaModels] = useState([]);
  const [defaultModel, setDefaultModel] = useState("qwen2.5:7b");
  const [modelsWarning, setModelsWarning] = useState("");
  const [selectedSubjectModel, setSelectedSubjectModel] = useState("");
  const [newEvaluation, setNewEvaluation] = useState({
    title: "",
    topic: "",
    num_questions: 5,
  });
  const [editingEvaluationId, setEditingEvaluationId] = useState(null);
  const [editEvaluation, setEditEvaluation] = useState({
    title: "",
    topic: "",
    num_questions: 5,
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [newTeacherEmail, setNewTeacherEmail] = useState("");

  const isUploading = Boolean(uploadProgress?.active);
  const selectedSubject = subjects.find((subject) => subject.id === selectedSubjectId);
  const evaluationSubjectHasDocs = (selectedSubject?.ingested_count ?? 0) > 0;

  const subjectsPagination = usePagination(subjects, 5);
  const documentsPagination = usePagination(documents, 5);
  const evaluationsPagination = usePagination(evaluations, 5);
  const labsPagination = usePagination(labs, 5);
  const labDocumentsPagination = usePagination(labDocuments, 5);
  const labSessionsPagination = usePagination(labSessions, 5);

  const handleTabChange = (nextTab) => {
    setTab(nextTab);
    if (nextTab === "labs") {
      setSelectedLab(null);
      setSelectedLabId(null);
      setViewingSession(null);
      setSessionChat(null);
    } else if (nextTab === "metrics" || nextTab === "wordcloud") {
      setViewingSession(null);
      setSessionChat(null);
    }
  };

  const loadSubjects = async () => {
    const data = await api.getMySubjects();
    setSubjects(data.subjects);
    if (data.subjects.length > 0 && !selectedSubjectId) {
      setSelectedSubjectId(data.subjects[0].id);
    }
  };

  const loadDocuments = async (subjectId) => {
    if (!subjectId) return;
    const data = await api.getDocuments(subjectId);
    setDocuments(data.documents);
  };

  const loadEvaluations = async (subjectId) => {
    if (!subjectId) return;
    const data = await api.getEvaluations(subjectId);
    setEvaluations(data.evaluations);
  };

  const loadLabs = async (subjectId) => {
    if (!subjectId) return;
    const data = await api.getLabs(subjectId);
    setLabs(data.labs);
  };

  const loadLabSessions = async (labId) => {
    const data = await api.getLabSessions(labId);
    setLabSessions(data.sessions);
    setSelectedLab(data.lab);
    setSelectedLabId(labId);
    const docs = await api.getLabDocuments(labId);
    setLabDocuments(docs.documents);
  };

  const handleUploadLabDocs = async () => {
    if (!selectedLabId || labFiles.length === 0) return;

    setError("");
    setMessage("");
    setLoading(true);
    setUploadProgress({
      active: true,
      current: 0,
      total: labFiles.length,
      filename: "",
      percent: 0,
      status: "uploading",
    });

    try {
      const data = await api.uploadLabDocuments(selectedLabId, labFiles, (progress) => {
        setUploadProgress({ active: true, ...progress });
      });
      const okCount = data.results.filter((r) => r.ok).length;
      setMessage(`${okCount} documento(s) del laboratorio procesado(s).`);
      setLabFiles([]);
      await loadLabs(selectedSubjectId);
      await loadLabSessions(selectedLabId);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadProgress(null);
      setLoading(false);
    }
  };

  const viewSessionChat = async (sessionId) => {
    setError("");
    try {
      const data = await api.getLabSession(sessionId);
      setSessionChat(data);
      setViewingSession(sessionId);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDownloadSessionPdf = async (sessionId) => {
    setError("");
    try {
      await api.downloadLabChatPdf(sessionId);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDownloadEvidence = async (sessionId, evidenceId, filename) => {
    setError("");
    try {
      await api.downloadLabEvidence(sessionId, evidenceId, filename);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadOllamaModels = async () => {
    const data = await api.getOllamaModels();
    setOllamaModels(data.models || []);
    setLlamaModels(data.llama_models || []);
    setDefaultModel(data.default_model || "qwen2.5:7b");
    setModelsWarning(data.warning || "");
    if (!newSubject.llm_model && data.default_model) {
      const defaultIsAvailable = (data.models || []).some(
        (model) =>
          model.name === data.default_model ||
          model.name.startsWith(`${data.default_model.split(":")[0]}:`),
      );
      if (defaultIsAvailable) {
        setNewSubject((current) => ({
          ...current,
          llm_model: data.default_model,
        }));
      }
    }
  };

  const openSessionFromMetrics = async (sessionId) => {
    setTab("labs");
    await viewSessionChat(sessionId);
  };

  useEffect(() => {
    Promise.all([loadSubjects(), loadOllamaModels()]).catch((err) =>
      setError(err.message),
    );
  }, []);

  useEffect(() => {
    const selected = subjects.find((subject) => subject.id === selectedSubjectId);
    setSelectedSubjectModel(selected?.llm_model || defaultModel);
  }, [subjects, selectedSubjectId, defaultModel]);

  useEffect(() => {
    if (selectedSubjectId) {
      loadDocuments(selectedSubjectId).catch((err) => setError(err.message));
      loadEvaluations(selectedSubjectId).catch((err) => setError(err.message));
      loadLabs(selectedSubjectId).catch((err) => setError(err.message));
    }
  }, [selectedSubjectId]);

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.createSubject(
        newSubject.name,
        newSubject.description,
        newSubject.llm_model,
      );
      setNewSubject({ name: "", description: "", llm_model: defaultModel });
      setMessage("Asignatura creada.");
      await loadSubjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSubjectModel = async () => {
    if (!selectedSubjectId) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.updateSubject(selectedSubjectId, { llm_model: selectedSubjectModel });
      setMessage("Modelo de IA actualizado para la asignatura.");
      await loadSubjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSubjectTeacher = async (e) => {
    e.preventDefault();
    if (!selectedSubjectId || !newTeacherEmail.trim()) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.addSubjectTeacher(selectedSubjectId, newTeacherEmail.trim());
      setNewTeacherEmail("");
      setMessage("Docente agregado a la asignatura.");
      await loadSubjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveSubjectTeacher = async (teacherId, teacherName) => {
    if (!selectedSubjectId) return;

    const confirmed = await confirmAction({
      title: "Quitar docente",
      text: `¿Quitar a «${teacherName}» como docente de esta asignatura?`,
      confirmText: "Quitar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.removeSubjectTeacher(selectedSubjectId, teacherId);
      setMessage("Docente removido de la asignatura.");
      await loadSubjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSubject = async () => {
    if (!selectedSubjectId || !selectedSubject?.can_delete) return;

    const confirmed = await confirmAction({
      title: "Eliminar asignatura",
      text: `¿Eliminar «${selectedSubject.name}»? Se borrarán documentos, evaluaciones, laboratorios, inscripciones y datos asociados. Esta acción no se puede deshacer.`,
      confirmText: "Eliminar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const data = await api.deleteSubject(selectedSubjectId);
      setMessage(
        `${data.message || "Asignatura eliminada."}${
          data.chunks_removed
            ? ` (${data.chunks_removed} fragmentos eliminados de la base de conocimiento)`
            : ""
        }`,
      );
      setSelectedSubjectId(null);
      await loadSubjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isModelDownloaded = (modelName) =>
    ollamaModels.some((model) => model.name === modelName);

  const modelPullHint = (modelName) => {
    const base = (modelName || "").split(":")[0];
    return base ? `ollama pull ${base}` : "";
  };

  const renderModelOptions = (models, label) =>
    models.length > 0 ? (
      <optgroup label={label}>
        {models.map((model) => (
          <option key={model.name} value={model.name}>
            {model.name}
          </option>
        ))}
      </optgroup>
    ) : null;

  const renderMissingModelOption = (value) =>
    value && !isModelDownloaded(value) ? (
      <option value={value} disabled>
        {value} (no descargado)
      </option>
    ) : null;

  const handleCreateEvaluation = async (e) => {
    e.preventDefault();
    if (!selectedSubjectId) return;

    if (!evaluationSubjectHasDocs) {
      setError(
        "Sube y procesa documentos PDF en la asignatura antes de crear evaluaciones.",
      );
      return;
    }

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.createEvaluation({
        subject_id: selectedSubjectId,
        title: newEvaluation.title,
        topic: newEvaluation.topic,
        num_questions: Number(newEvaluation.num_questions),
      });
      setNewEvaluation({ title: "", topic: "", num_questions: 5 });
      setMessage("Evaluación creada.");
      await loadEvaluations(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startEditEvaluation = (evaluation) => {
    setEditingEvaluationId(evaluation.id);
    setEditEvaluation({
      title: evaluation.title,
      topic: evaluation.topic,
      num_questions: evaluation.num_questions,
    });
  };

  const cancelEditEvaluation = () => {
    setEditingEvaluationId(null);
    setEditEvaluation({ title: "", topic: "", num_questions: 5 });
  };

  const handleUpdateEvaluation = async (e) => {
    e.preventDefault();
    if (!editingEvaluationId) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.updateEvaluation(editingEvaluationId, {
        title: editEvaluation.title,
        topic: editEvaluation.topic,
        num_questions: Number(editEvaluation.num_questions),
      });
      setMessage("Evaluación actualizada.");
      cancelEditEvaluation();
      await loadEvaluations(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEvaluation = async (evaluation) => {
    const attemptsNote =
      evaluation.attempt_count > 0
        ? ` Se eliminarán ${evaluation.attempt_count} intento(s) de estudiantes.`
        : "";
    const confirmed = await confirmAction({
      title: "Eliminar evaluación",
      text: `¿Eliminar la evaluación «${evaluation.title}»?${attemptsNote}`,
      confirmText: "Eliminar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const data = await api.deleteEvaluation(evaluation.id);
      setMessage(
        `${data.message || "Evaluación eliminada."}${
          data.attempts_removed
            ? ` (${data.attempts_removed} intento(s) eliminado(s))`
            : ""
        }`,
      );
      if (editingEvaluationId === evaluation.id) {
        cancelEditEvaluation();
      }
      await loadEvaluations(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateLab = async (e) => {
    e.preventDefault();
    if (!selectedSubjectId) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.createLab({
        subject_id: selectedSubjectId,
        title: newLab.title,
        topic: newLab.topic,
        instructions: newLab.instructions,
      });
      setNewLab({ title: "", topic: "", instructions: "" });
      setMessage("Laboratorio creado.");
      await loadLabs(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
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
      const data = await api.uploadDocuments(selectedSubjectId, files, (progress) => {
        setUploadProgress({ active: true, ...progress });
      });
      const okCount = data.results.filter((r) => r.ok).length;
      setMessage(`${okCount} documento(s) procesado(s).`);
      setFiles([]);
      await loadSubjects();
      await loadDocuments(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadProgress(null);
      setLoading(false);
    }
  };

  const handleDeleteSubjectDocument = async (documentId, filename) => {
    const confirmed = await confirmAction({
      title: "Eliminar documento",
      text: `¿Eliminar «${filename}»? Se quitará del disco y de la base de conocimiento del modelo.`,
      confirmText: "Eliminar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const data = await api.deleteSubjectDocument(documentId);
      setMessage(
        `${data.message}${data.chunks_removed ? ` (${data.chunks_removed} fragmentos eliminados)` : ""}`,
      );
      await loadSubjects();
      await loadDocuments(selectedSubjectId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteLabDocument = async (documentId, filename) => {
    const confirmed = await confirmAction({
      title: "Eliminar documento",
      text: `¿Eliminar «${filename}» del laboratorio? Se quitará del conocimiento del asistente.`,
      confirmText: "Eliminar",
      danger: true,
    });
    if (!confirmed) return;

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const data = await api.deleteLabDocument(documentId);
      setMessage(
        `${data.message}${data.chunks_removed ? ` (${data.chunks_removed} fragmentos eliminados)` : ""}`,
      );
      await loadLabs(selectedSubjectId);
      if (selectedLabId) {
        await loadLabSessions(selectedLabId);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h2>Panel Docente</h2>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <ResponsiveNav items={TEACHER_TABS} activeId={tab} onSelect={handleTabChange} />

      {tab === "subjects" && (
        <>
          <section className="card">
            <h3>Crear asignatura</h3>
            <form onSubmit={handleCreateSubject} className="form inline-form">
              <label>
                Nombre
                <input
                  value={newSubject.name}
                  onChange={(e) =>
                    setNewSubject({ ...newSubject, name: e.target.value })
                  }
                  required
                />
              </label>
              <label>
                Descripción
                <input
                  value={newSubject.description}
                  onChange={(e) =>
                    setNewSubject({ ...newSubject, description: e.target.value })
                  }
                />
              </label>
              <label>
                Modelo Ollama
                <select
                  value={newSubject.llm_model}
                  onChange={(e) =>
                    setNewSubject({ ...newSubject, llm_model: e.target.value })
                  }
                >
                  {renderMissingModelOption(newSubject.llm_model)}
                  {renderModelOptions(llamaModels, "Llama")}
                  {renderModelOptions(
                    ollamaModels.filter(
                      (model) =>
                        !llamaModels.some((llama) => llama.name === model.name),
                    ),
                    "Otros modelos",
                  )}
                  {ollamaModels.length === 0 && (
                    <option value={defaultModel}>{defaultModel}</option>
                  )}
                </select>
              </label>
              {modelsWarning && <p className="muted">{modelsWarning}</p>}
              {!isModelDownloaded(newSubject.llm_model) && newSubject.llm_model && (
                <p className="error">
                  Selecciona un modelo descargado o ejecuta:{" "}
                  <code>{modelPullHint(newSubject.llm_model)}</code>
                </p>
              )}
              <button
                type="submit"
                className="btn-primary"
                disabled={
                  loading ||
                  (ollamaModels.length > 0 &&
                    newSubject.llm_model &&
                    !isModelDownloaded(newSubject.llm_model))
                }
              >
                Crear
              </button>
            </form>
          </section>

          <section className="card">
            <h3>Mis asignaturas</h3>
            {subjects.length === 0 ? (
              <p className="muted">Aún no has creado ninguna asignatura.</p>
            ) : (
              <>
              <ul className="list">
                {subjectsPagination.pageItems.map((s) => (
                  <li
                    key={s.id}
                    className={
                      selectedSubjectId === s.id ? "list-item active" : "list-item"
                    }
                    onClick={() => setSelectedSubjectId(s.id)}
                  >
                    <strong>{s.name}</strong>
                    {s.description && <p>{s.description}</p>}
                    <span className="muted">
                      Modelo: {s.llm_model || defaultModel}
                      {s.llm_model_available === false && (
                        <span className="badge-warning"> · no descargado</span>
                      )}
                    </span>
                    <span className="muted">
                      {s.ingested_count}/{s.document_count} documentos procesados
                    </span>
                    {s.teachers?.length > 0 && (
                      <span className="muted">{formatSubjectTeachers(s)}</span>
                    )}
                  </li>
                ))}
              </ul>
              <Pagination
                page={subjectsPagination.page}
                totalPages={subjectsPagination.totalPages}
                totalItems={subjectsPagination.totalItems}
                pageSize={subjectsPagination.pageSize}
                onPageChange={subjectsPagination.setPage}
              />
              </>
            )}

            {selectedSubjectId && selectedSubject && (
              <div className="subject-teachers-panel">
                <h4>Docentes de la asignatura</h4>
                <p className="muted">
                  Varios docentes pueden gestionar documentos, evaluaciones y laboratorios.
                </p>
                <ul className="teacher-tags">
                  {(selectedSubject.teachers || []).map((teacher) => (
                    <li key={teacher.id} className="teacher-tag">
                      <span>
                        {teacher.nombre}
                        {teacher.is_primary && (
                          <span className="badge">Principal</span>
                        )}
                      </span>
                      {!teacher.is_primary && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() =>
                            handleRemoveSubjectTeacher(teacher.id, teacher.nombre)
                          }
                          disabled={loading}
                        >
                          Quitar
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <form onSubmit={handleAddSubjectTeacher} className="form inline-form">
                  <label>
                    Agregar docente por correo
                    <input
                      type="email"
                      value={newTeacherEmail}
                      onChange={(e) => setNewTeacherEmail(e.target.value)}
                      placeholder="correo@unal.edu.co"
                    />
                  </label>
                  <button
                    type="submit"
                    className="btn-secondary"
                    disabled={loading || !newTeacherEmail.trim()}
                  >
                    Agregar docente
                  </button>
                </form>
              </div>
            )}

            {selectedSubjectId && (
              <div className="subject-model-panel">
                <h4>Modelo de IA de la asignatura</h4>
                <p className="muted">
                  Se usará en práctica libre, evaluaciones y chat de laboratorios.
                </p>
                <label>
                  Modelo Ollama
                  <select
                    value={selectedSubjectModel}
                    onChange={(e) => setSelectedSubjectModel(e.target.value)}
                  >
                    {renderMissingModelOption(selectedSubjectModel)}
                    {renderModelOptions(llamaModels, "Llama")}
                    {renderModelOptions(
                      ollamaModels.filter(
                        (model) =>
                          !llamaModels.some((llama) => llama.name === model.name),
                      ),
                      "Otros modelos",
                    )}
                    {ollamaModels.length === 0 && (
                      <option value={defaultModel}>{defaultModel}</option>
                    )}
                  </select>
                </label>
                {!isModelDownloaded(selectedSubjectModel) && selectedSubjectModel && (
                  <p className="error">
                    Este modelo no está descargado. Ejecuta:{" "}
                    <code>{modelPullHint(selectedSubjectModel)}</code>
                  </p>
                )}
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleUpdateSubjectModel}
                  disabled={
                    loading ||
                    (ollamaModels.length > 0 &&
                      selectedSubjectModel &&
                      !isModelDownloaded(selectedSubjectModel))
                  }
                >
                  Guardar modelo
                </button>
              </div>
            )}

            {selectedSubjectId && selectedSubject?.can_delete && (
              <div className="subject-danger-panel">
                <h4>Zona de peligro</h4>
                <p className="muted">
                  Solo tú, como docente que creó esta asignatura, puedes eliminarla
                  permanentemente.
                </p>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleDeleteSubject}
                  disabled={loading}
                >
                  Eliminar asignatura
                </button>
              </div>
            )}
          </section>
        </>
      )}

      {tab === "documents" && (
        <section className="card">
          <h3>Subir documentos</h3>
          {subjects.length === 0 ? (
            <p className="muted">Primero crea una asignatura.</p>
          ) : (
            <>
              <label>
                Asignatura
                <select
                  value={selectedSubjectId || ""}
                  onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="file-input">
                PDFs
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files))}
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
                {isUploading ? "Procesando..." : "Procesar documentos"}
              </button>

              <h4>Documentos cargados</h4>
              {documents.length === 0 ? (
                <p className="muted">No hay documentos.</p>
              ) : (
                <>
                <ul className="list compact">
                  {documentsPagination.pageItems.map((d) => (
                    <li key={d.id} className="document-item">
                      <span>
                        {d.filename} — {d.ingested ? "Procesado" : "Pendiente"}
                      </span>
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => handleDeleteSubjectDocument(d.id, d.filename)}
                        disabled={loading}
                      >
                        Eliminar
                      </button>
                    </li>
                  ))}
                </ul>
                <Pagination
                  page={documentsPagination.page}
                  totalPages={documentsPagination.totalPages}
                  totalItems={documentsPagination.totalItems}
                  pageSize={documentsPagination.pageSize}
                  onPageChange={documentsPagination.setPage}
                />
                </>
              )}
            </>
          )}
        </section>
      )}

      {tab === "evaluations" && (
        <div className="grid-2">
          <section className="card">
            <h3>Crear evaluación</h3>
            {subjects.length === 0 ? (
              <p className="muted">Primero crea una asignatura.</p>
            ) : (
              <form onSubmit={handleCreateEvaluation} className="form">
                <p className="muted">
                  Las preguntas se generan únicamente a partir de los PDFs procesados
                  de la asignatura (no usa conocimiento externo).
                </p>
                {!evaluationSubjectHasDocs && (
                  <p className="error">
                    Esta asignatura no tiene documentos procesados. Ve a la pestaña
                    «Documentos» y sube PDFs antes de crear evaluaciones.
                  </p>
                )}
                <label>
                  Asignatura
                  <select
                    value={selectedSubjectId || ""}
                    onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                  >
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Título (opcional)
                  <input
                    value={newEvaluation.title}
                    onChange={(e) =>
                      setNewEvaluation({ ...newEvaluation, title: e.target.value })
                    }
                    placeholder="Ej. Parcial 1 — Derivadas"
                  />
                </label>

                <label>
                  Tema de la evaluación
                  <input
                    value={newEvaluation.topic}
                    onChange={(e) =>
                      setNewEvaluation({ ...newEvaluation, topic: e.target.value })
                    }
                    placeholder="Ej. Límites y continuidad"
                    required
                  />
                </label>

                <label>
                  Número de preguntas
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={newEvaluation.num_questions}
                    onChange={(e) =>
                      setNewEvaluation({
                        ...newEvaluation,
                        num_questions: e.target.value,
                      })
                    }
                    required
                  />
                </label>

                <button
                  type="submit"
                  className="btn-primary"
                  disabled={loading || !evaluationSubjectHasDocs}
                >
                  Crear evaluación
                </button>
              </form>
            )}
          </section>

          <section className="card">
            <h3>Evaluaciones creadas</h3>
            {evaluations.length === 0 ? (
              <p className="muted">No hay evaluaciones para esta asignatura.</p>
            ) : (
              <>
              <ul className="list">
                {evaluationsPagination.pageItems.map((ev) => (
                  <li key={ev.id} className="list-item static evaluation-item">
                    {editingEvaluationId === ev.id ? (
                      <form onSubmit={handleUpdateEvaluation} className="form">
                        <label>
                          Título
                          <input
                            value={editEvaluation.title}
                            onChange={(e) =>
                              setEditEvaluation({
                                ...editEvaluation,
                                title: e.target.value,
                              })
                            }
                            required
                          />
                        </label>
                        <label>
                          Tema
                          <input
                            value={editEvaluation.topic}
                            onChange={(e) =>
                              setEditEvaluation({
                                ...editEvaluation,
                                topic: e.target.value,
                              })
                            }
                            required
                          />
                        </label>
                        <label>
                          Número de preguntas
                          <input
                            type="number"
                            min={1}
                            max={20}
                            value={editEvaluation.num_questions}
                            onChange={(e) =>
                              setEditEvaluation({
                                ...editEvaluation,
                                num_questions: e.target.value,
                              })
                            }
                            required
                          />
                        </label>
                        <div className="button-group">
                          <button
                            type="submit"
                            className="btn-primary btn-sm"
                            disabled={loading}
                          >
                            Guardar
                          </button>
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            onClick={cancelEditEvaluation}
                            disabled={loading}
                          >
                            Cancelar
                          </button>
                        </div>
                      </form>
                    ) : (
                      <div className="row-between">
                        <div>
                          <strong>{ev.title}</strong>
                          <p className="muted">Tema: {ev.topic}</p>
                          <p className="muted">
                            {ev.num_questions} preguntas
                            {ev.attempt_count > 0 && (
                              <span> · {ev.attempt_count} intento(s)</span>
                            )}
                          </p>
                        </div>
                        <div className="button-group">
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            onClick={() => startEditEvaluation(ev)}
                            disabled={loading}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            onClick={() => handleDeleteEvaluation(ev)}
                            disabled={loading}
                          >
                            Eliminar
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              <Pagination
                page={evaluationsPagination.page}
                totalPages={evaluationsPagination.totalPages}
                totalItems={evaluationsPagination.totalItems}
                pageSize={evaluationsPagination.pageSize}
                onPageChange={evaluationsPagination.setPage}
              />
              </>
            )}
          </section>
        </div>
      )}

      {tab === "labs" && !viewingSession && (
        <div className="grid-2">
          <section className="card">
            <h3>Crear laboratorio</h3>
            {subjects.length === 0 ? (
              <p className="muted">Primero crea una asignatura.</p>
            ) : (
              <form onSubmit={handleCreateLab} className="form">
                <label>
                  Asignatura
                  <select
                    value={selectedSubjectId || ""}
                    onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                  >
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Título
                  <input
                    value={newLab.title}
                    onChange={(e) => setNewLab({ ...newLab, title: e.target.value })}
                    placeholder="Ej. Lab 1 — Manejo de la terminal"
                    required
                  />
                </label>

                <label>
                  Tema (para la base de conocimiento)
                  <input
                    value={newLab.topic}
                    onChange={(e) => setNewLab({ ...newLab, topic: e.target.value })}
                    placeholder="Ej. comandos terminal linux"
                    required
                  />
                </label>

                <label>
                  Instrucciones del laboratorio
                  <textarea
                    rows={8}
                    value={newLab.instructions}
                    onChange={(e) =>
                      setNewLab({ ...newLab, instructions: e.target.value })
                    }
                    placeholder={"1. Abre la terminal\n2. Ejecuta el comando ls\n3. ..."}
                    required
                  />
                </label>

                <button type="submit" className="btn-primary" disabled={loading}>
                  Crear laboratorio
                </button>
              </form>
            )}
          </section>

          <section className="card">
            <h3>Laboratorios creados</h3>
            {labs.length === 0 ? (
              <p className="muted">No hay laboratorios para esta asignatura.</p>
            ) : (
              <>
              <ul className="list">
                {labsPagination.pageItems.map((lab) => (
                  <li
                    key={lab.id}
                    className={
                      selectedLabId === lab.id ? "list-item active" : "list-item"
                    }
                    onClick={() => loadLabSessions(lab.id)}
                  >
                    <strong>{lab.title}</strong>
                    <p className="muted">Tema: {lab.topic}</p>
                    <span className="muted">
                      {lab.ingested_count}/{lab.document_count} documentos procesados
                    </span>
                  </li>
                ))}
              </ul>
              <Pagination
                page={labsPagination.page}
                totalPages={labsPagination.totalPages}
                totalItems={labsPagination.totalItems}
                pageSize={labsPagination.pageSize}
                onPageChange={labsPagination.setPage}
              />
              </>
            )}

            {selectedLab && (
              <>
                <h4>Documentos — {selectedLab.title}</h4>
                <label className="file-input">
                  PDFs del laboratorio
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={(e) => setLabFiles(Array.from(e.target.files))}
                  />
                </label>
                {labFiles.length > 0 && (
                  <p className="muted">{labFiles.length} archivo(s) seleccionado(s)</p>
                )}
                <UploadProgress progress={uploadProgress} />
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleUploadLabDocs}
                  disabled={loading || isUploading || labFiles.length === 0}
                >
                  {isUploading ? "Procesando..." : "Procesar documentos"}
                </button>
                {labDocuments.length === 0 ? (
                  <p className="muted">No hay documentos para este laboratorio.</p>
                ) : (
                  <>
                  <ul className="list compact">
                    {labDocumentsPagination.pageItems.map((d) => (
                      <li key={d.id} className="document-item">
                        <span>
                          {d.filename} — {d.ingested ? "Procesado" : "Pendiente"}
                        </span>
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => handleDeleteLabDocument(d.id, d.filename)}
                          disabled={loading}
                        >
                          Eliminar
                        </button>
                      </li>
                    ))}
                  </ul>
                  <Pagination
                    page={labDocumentsPagination.page}
                    totalPages={labDocumentsPagination.totalPages}
                    totalItems={labDocumentsPagination.totalItems}
                    pageSize={labDocumentsPagination.pageSize}
                    onPageChange={labDocumentsPagination.setPage}
                  />
                  </>
                )}

                <h4>Sesiones — {selectedLab.title}</h4>
                {labSessions.length === 0 ? (
                  <p className="muted">Ningún estudiante ha iniciado este lab.</p>
                ) : (
                  <>
                  <ul className="list">
                    {labSessionsPagination.pageItems.map((s) => (
                      <li key={s.session_id} className="list-item static">
                        <div className="row-between">
                          <div>
                            <strong>{s.student_name}</strong>
                            <p className="muted">
                              {s.message_count} mensajes · {s.evidence_count} evidencias · {s.status}
                            </p>
                          </div>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => viewSessionChat(s.session_id)}
                          >
                            Ver chat
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                  <Pagination
                    page={labSessionsPagination.page}
                    totalPages={labSessionsPagination.totalPages}
                    totalItems={labSessionsPagination.totalItems}
                    pageSize={labSessionsPagination.pageSize}
                    onPageChange={labSessionsPagination.setPage}
                  />
                  </>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {tab === "metrics" && !viewingSession && (
        <TeacherMetrics
          subjects={subjects}
          onViewLabSession={openSessionFromMetrics}
        />
      )}

      {tab === "wordcloud" && !viewingSession && (
        <TeacherWordCloud
          subjects={subjects}
          selectedSubjectId={selectedSubjectId}
          onSubjectChange={setSelectedSubjectId}
        />
      )}

      {viewingSession && sessionChat && (
        <section className="card">
          <div className="row-between">
            <div>
              <h3>Chat del estudiante: {sessionChat.student_name}</h3>
              <p className="muted">{sessionChat.session.lab?.title}</p>
            </div>
            <div className="button-group">
              <button
                type="button"
                className="btn-primary"
                onClick={() => handleDownloadSessionPdf(viewingSession)}
              >
                Exportar PDF
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setViewingSession(null);
                  setSessionChat(null);
                }}
              >
                Volver
              </button>
            </div>
          </div>

          <h4>Evidencia entregada</h4>
          {!sessionChat.evidence?.length ? (
            <p className="muted">El estudiante no ha subido evidencia.</p>
          ) : (
            <ul className="list">
              {sessionChat.evidence.map((item) => (
                <li key={item.id} className="list-item static">
                  <div className="row-between">
                    <div>
                      <strong>{item.filename}</strong>
                      {item.note && <p className="muted">{item.note}</p>}
                      {item.uploaded_at && (
                        <p className="muted">
                          {new Date(item.uploaded_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() =>
                        handleDownloadEvidence(viewingSession, item.id, item.filename)
                      }
                    >
                      Descargar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <h4>Chat</h4>
          <div className="teacher-chat-view">
            {sessionChat.messages.map((msg) => (
              <div
                key={msg.id}
                className={msg.role === "user" ? "chat-bubble user" : "chat-bubble assistant"}
              >
                <span className="chat-role">
                  {msg.role === "user" ? sessionChat.student_name : "Asistente"}
                </span>
                <p>{msg.content}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
