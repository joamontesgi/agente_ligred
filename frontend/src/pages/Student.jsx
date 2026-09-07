import { useEffect, useState } from "react";
import { api } from "../api/client";
import LabChat from "../components/LabChat";
import Pagination from "../components/Pagination";
import ResponsiveNav from "../components/ResponsiveNav";
import { usePagination } from "../hooks/usePagination";
import { formatSubjectTeachers } from "../utils/subjectTeachers";
import LoadingSpinner from "../components/LoadingSpinner";

const STUDENT_TABS = [
  { id: "evaluations", label: "Evaluaciones" },
  { id: "labs", label: "Laboratorios" },
  { id: "practice", label: "Práctica libre" },
  { id: "enroll", label: "Inscribirme" },
];

export default function Student() {
  const [tab, setTab] = useState("evaluations");
  const [subjects, setSubjects] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [availableEvaluations, setAvailableEvaluations] = useState([]);
  const [availableLabs, setAvailableLabs] = useState([]);
  const [activeLabSession, setActiveLabSession] = useState(null);
  const [labReadOnly, setLabReadOnly] = useState(false);

  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [contexto, setContexto] = useState("");
  const [fuente, setFuente] = useState("");
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState("");
  const [stats, setStats] = useState({ preguntas: 0, aciertos: 0 });

  const [examPhase, setExamPhase] = useState("list");
  const [activeExam, setActiveExam] = useState(null);
  const [examAnswers, setExamAnswers] = useState({});
  const [examResults, setExamResults] = useState(null);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [examLoading, setExamLoading] = useState(false);
  const [examLoadingMessage, setExamLoadingMessage] = useState("");

  const subjectsPagination = usePagination(subjects, 5);
  const labsPagination = usePagination(availableLabs, 5);
  const evaluationsPagination = usePagination(availableEvaluations, 5);

  const evaluationHasDocuments = (ev) =>
    Boolean(
      ev.has_documents ??
      (ev.ingested_document_count ?? 0) > 0,
    );

  const handleTabChange = (nextTab) => {
    setTab(nextTab);
    if (nextTab === "labs") {
      setActiveLabSession(null);
    }
  };

  const loadData = async () => {
    const [allSubjects, myEnrollments, evaluations, labs] = await Promise.all([
      api.getAllSubjects(),
      api.getEnrollments(),
      api.getAvailableEvaluations(),
      api.getAvailableLabs(),
    ]);
    setSubjects(allSubjects.subjects);
    setEnrollments(myEnrollments.enrollments);
    setAvailableEvaluations(evaluations.evaluations);
    setAvailableLabs(labs.labs);
    if (myEnrollments.enrollments.length > 0 && !selectedSubjectId) {
      setSelectedSubjectId(myEnrollments.enrollments[0].subject_id);
    }
  };

  useEffect(() => {
    loadData().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (tab === "evaluations" && examPhase === "list") {
      api
        .getAvailableEvaluations()
        .then((data) => setAvailableEvaluations(data.evaluations))
        .catch((err) => setError(err.message));
    }
  }, [tab, examPhase]);

  const handleEnroll = async (subjectId) => {
    setError("");
    setMessage("");
    try {
      const data = await api.enroll(subjectId);
      setMessage(data.message);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleNewQuestion = async () => {
    if (!selectedSubjectId) return;

    setError("");
    setEvaluation("");
    setAnswer("");
    setLoading(true);

    try {
      const data = await api.generateQuestion(selectedSubjectId);
      setQuestion(data.pregunta);
      setContexto(data.contexto);
      setFuente(data.fuente);
    } catch (err) {
      setError(err.message);
      setQuestion(null);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    if (!question || !answer.trim()) return;

    setError("");
    setLoading(true);

    try {
      const data = await api.evaluateAnswer({
        subject_id: selectedSubjectId,
        contexto,
        pregunta: question,
        respuesta: answer,
      });

      setEvaluation(data.evaluacion);
      setStats((prev) => ({
        preguntas: prev.preguntas + 1,
        aciertos: prev.aciertos + (data.correcta ? 1 : 0),
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartExam = async (evalId) => {
    setError("");
    setLoading(true);
    setExamLoading(true);
    setExamLoadingMessage("Generando preguntas a partir de los documentos...");

    try {
      const data = await api.startEvaluation(evalId);

      setActiveExam(data);
      const initialAnswers = {};
      for (const q of data.questions) {
        initialAnswers[q.question_number] = q.respuesta_estudiante || "";
      }
      setExamAnswers(initialAnswers);
      setExamResults(null);
      setExamPhase("taking");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setExamLoading(false);
      setExamLoadingMessage("");
    }
  };

  const handleSubmitExam = async () => {
    if (!activeExam) return;

    setError("");
    setLoading(true);
    setExamLoading(true);
    setExamLoadingMessage("Enviando respuestas y calificando evaluación...");

    try {
      const answers = activeExam.questions.map((q) => ({
        question_number: q.question_number,
        respuesta: examAnswers[q.question_number] || "",
      }));

      const data = await api.submitEvaluation(activeExam.attempt_id, answers);
      setExamResults(data);
      setExamPhase("results");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setExamLoading(false);
      setExamLoadingMessage("");
    }
  };

  const handleDownloadPdf = async () => {
    if (!examResults?.attempt?.id) return;

    setError("");
    try {
      await api.downloadAttemptPdf(examResults.attempt.id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleBackToList = () => {
    setExamPhase("list");
    setActiveExam(null);
    setExamAnswers({});
    setExamResults(null);
  };

  const handleStartLab = async (labId) => {
    setError("");
    setLoading(true);
    try {
      const data = await api.startLab(labId);
      setActiveLabSession(data.session);
      setLabReadOnly(data.read_only || false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLabComplete = async () => {
    setLabReadOnly(true);
    setMessage("Laboratorio finalizado.");
    await loadData();
  };

  const handleBackFromLab = () => {
    setActiveLabSession(null);
    setLabReadOnly(false);
    loadData().catch(() => {});
  };

  const score =
    stats.preguntas > 0
      ? ((stats.aciertos / stats.preguntas) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="page">
      <h2>Área del estudiante</h2>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <ResponsiveNav items={STUDENT_TABS} activeId={tab} onSelect={handleTabChange} />

      {tab === "evaluations" && examLoading && (
        <div className="exam-loading-overlay">
          <LoadingSpinner label={examLoadingMessage} />
        </div>
      )}

      {tab === "enroll" && (
        <section className="card">
          <h3>Asignaturas disponibles</h3>
          {subjects.length === 0 ? (
            <p className="muted">No hay asignaturas disponibles.</p>
          ) : (
            <>
            <ul className="list">
              {subjectsPagination.pageItems.map((s) => (
                <li key={s.id} className="list-item static">
                  <div className="row-between">
                    <div>
                      <strong>{s.name}</strong>
                      <p className="muted">{formatSubjectTeachers(s)}</p>
                      {s.description && <p>{s.description}</p>}
                    </div>
                    {s.enrolled ? (
                      <span className="badge success">Inscrito</span>
                    ) : (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleEnroll(s.id)}
                      >
                        Inscribirme
                      </button>
                    )}
                  </div>
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
        </section>
      )}

      {tab === "labs" && !activeLabSession && (
        <section className="card">
          <h3>Laboratorios disponibles</h3>
          {availableLabs.length === 0 ? (
            <p className="muted">
              No hay laboratorios disponibles. Inscríbete en una asignatura.
            </p>
          ) : (
            <>
            <ul className="list">
              {labsPagination.pageItems.map((lab) => (
                <li key={lab.id} className="list-item static">
                  <div className="row-between">
                    <div>
                      <strong>{lab.title}</strong>
                      <p className="muted">{lab.subject_name}</p>
                      <p className="muted">Tema: {lab.topic}</p>
                      {lab.completed && (
                        <span className="badge success">Completado</span>
                      )}
                      {lab.in_progress && (
                        <span className="badge">En progreso</span>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={loading}
                      onClick={() => handleStartLab(lab.id)}
                    >
                      {lab.in_progress
                        ? "Continuar"
                        : lab.completed
                          ? "Ver chat"
                          : "Iniciar"}
                    </button>
                  </div>
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
        </section>
      )}

      {tab === "labs" && activeLabSession && (
        <LabChat
          sessionId={activeLabSession.id}
          lab={activeLabSession.lab}
          readOnly={labReadOnly}
          onComplete={handleLabComplete}
          onBack={handleBackFromLab}
        />
      )}

      {tab === "evaluations" && examPhase === "list" && (
        <section className="card">
          <h3>Evaluaciones disponibles</h3>
          <p className="muted">
            Cada evaluación genera preguntas solo con base en los documentos PDF
            procesados de la asignatura.
          </p>
          {availableEvaluations.length === 0 ? (
            <p className="muted">
              No hay evaluaciones disponibles. Inscríbete en una asignatura.
            </p>
          ) : (
            <>
            <ul className="list">
              {evaluationsPagination.pageItems.map((ev) => (
                <li key={ev.id} className="list-item static">
                  <div className="row-between">
                    <div>
                      <strong>{ev.title}</strong>
                      <p className="muted">{ev.subject_name}</p>
                      <p className="muted">
                        Tema: {ev.topic} · {ev.num_questions} preguntas
                      </p>
                      {!evaluationHasDocuments(ev) && (
                        <p className="error">
                          {ev.document_count > 0
                            ? `Hay ${ev.document_count} documento(s), pero ninguno está procesado todavía.`
                            : "Sin documentos procesados en la asignatura."}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={loading || !evaluationHasDocuments(ev)}
                      onClick={() => handleStartExam(ev.id)}
                    >
                      {!evaluationHasDocuments(ev)
                        ? "No disponible"
                        : ev.in_progress
                          ? "Continuar"
                          : "Iniciar"}
                    </button>
                  </div>
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
      )}

      {tab === "evaluations" && examPhase === "taking" && activeExam && (
        <section className="card">
          <div className="row-between">
            <div>
              <h3>{activeExam.evaluation.title}</h3>
              <p className="muted">Tema: {activeExam.evaluation.topic}</p>
            </div>
            <button type="button" className="btn-secondary" onClick={handleBackToList}>
              Cancelar
            </button>
          </div>

          {activeExam.questions.map((q) => (
            <div key={q.question_number} className="question-box">
              <h4>Pregunta {q.question_number}</h4>
              <p>{q.pregunta}</p>
              <label>
                Tu respuesta
                <textarea
                  rows={4}
                  value={examAnswers[q.question_number] || ""}
                  onChange={(e) =>
                    setExamAnswers({
                      ...examAnswers,
                      [q.question_number]: e.target.value,
                    })
                  }
                />
              </label>
            </div>
          ))}

          <button
            type="button"
            className="btn-primary"
            onClick={handleSubmitExam}
            disabled={loading}
          >
            {loading ? "Enviando..." : "Enviar evaluación"}
          </button>
        </section>
      )}

      {tab === "evaluations" && examPhase === "results" && examResults && (
        <section className="card">
          <div className="row-between">
            <div>
              <h3>Resultados</h3>
              <p className="muted">
                Puntuación: {examResults.attempt.score}% (
                {examResults.attempt.correct_count}/
                {examResults.attempt.total_questions} correctas)
              </p>
            </div>
            <div className="button-group">
              <button type="button" className="btn-primary" onClick={handleDownloadPdf}>
                Exportar PDF
              </button>
              <button type="button" className="btn-secondary" onClick={handleBackToList}>
                Volver
              </button>
            </div>
          </div>

          {examResults.answers.map((a) => (
            <div key={a.question_number} className="evaluation-box">
              <h4>
                Pregunta {a.question_number} —{" "}
                {a.correcta ? (
                  <span className="text-success">Correcta</span>
                ) : (
                  <span className="text-error">Incorrecta</span>
                )}
              </h4>
              <p>{a.pregunta}</p>
              <p className="muted">
                <strong>Tu respuesta:</strong> {a.respuesta_estudiante}
              </p>
              <pre>{a.evaluacion}</pre>
            </div>
          ))}
        </section>
      )}

      {tab === "practice" && (
        <div className="grid-2">
          <section className="card">
            {enrollments.length === 0 ? (
              <p className="muted">
                Inscríbete en una asignatura en la pestaña «Inscribirme».
              </p>
            ) : (
              <>
                <label>
                  Asignatura
                  <select
                    value={selectedSubjectId || ""}
                    onChange={(e) => {
                      setSelectedSubjectId(Number(e.target.value));
                      setQuestion(null);
                      setEvaluation("");
                      setAnswer("");
                    }}
                  >
                    {enrollments.map((e) => (
                      <option key={e.subject_id} value={e.subject_id}>
                        {e.subject_name}
                      </option>
                    ))}
                  </select>
                </label>

                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleNewQuestion}
                  disabled={loading}
                >
                  Nueva pregunta
                </button>

                {question && (
                  <div className="question-box">
                    <h3>Pregunta</h3>
                    <p>{question}</p>

                    <label>
                      Tu respuesta
                      <textarea
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        rows={5}
                      />
                    </label>

                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleEvaluate}
                      disabled={loading || !answer.trim()}
                    >
                      Enviar respuesta
                    </button>
                  </div>
                )}

                {evaluation && (
                  <div className="evaluation-box">
                    <h3>Evaluación</h3>
                    <pre>{evaluation}</pre>
                    {fuente && <p className="muted">Documento: {fuente}</p>}
                  </div>
                )}
              </>
            )}
          </section>

          <aside className="card stats">
            <h3>Progreso</h3>
            <div className="stat">
              <span>Preguntas</span>
              <strong>{stats.preguntas}</strong>
            </div>
            <div className="stat">
              <span>Aciertos</span>
              <strong>{stats.aciertos}</strong>
            </div>
            <div className="stat">
              <span>Puntuación</span>
              <strong>{score}%</strong>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
