import { useEffect, useState } from "react";
import { api } from "../api/client";
import Pagination from "./Pagination";
import { usePagination } from "../hooks/usePagination";

export default function TeacherMetrics({ subjects, onViewLabSession }) {
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (subjects.length > 0 && !selectedSubjectId) {
      setSelectedSubjectId(subjects[0].id);
    }
  }, [subjects, selectedSubjectId]);

  useEffect(() => {
    if (!selectedSubjectId) return;

    setLoading(true);
    setError("");
    api
      .getSubjectMetrics(selectedSubjectId)
      .then(setMetrics)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedSubjectId]);

  const labSessionsPagination = usePagination(metrics?.lab_sessions || [], 8);
  const evaluationAttemptsPagination = usePagination(
    metrics?.evaluation_attempts || [],
    8,
  );

  if (subjects.length === 0) {
    return <p className="muted">Crea una asignatura para ver métricas.</p>;
  }

  const summary = metrics?.summary;

  return (
    <div className="metrics-page">
      {error && <p className="error">{error}</p>}

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

      {loading && <p className="muted">Cargando métricas...</p>}

      {summary && (
        <div className="metrics-grid">
          <div className="metric-card">
            <span>Estudiantes inscritos</span>
            <strong>{summary.students_enrolled}</strong>
          </div>
          <div className="metric-card">
            <span>Labs completados</span>
            <strong>
              {summary.lab_sessions_completed}/{summary.lab_sessions_total}
            </strong>
          </div>
          <div className="metric-card">
            <span>Evaluaciones completadas</span>
            <strong>
              {summary.evaluation_attempts_completed}/{summary.evaluation_attempts_total}
            </strong>
          </div>
          <div className="metric-card">
            <span>Promedio evaluaciones</span>
            <strong>
              {summary.avg_evaluation_score != null
                ? `${summary.avg_evaluation_score}%`
                : "—"}
            </strong>
          </div>
        </div>
      )}

      {metrics && (
        <>
          <section className="card">
            <h3>Laboratorios — sesiones de estudiantes</h3>
            <p className="muted">
              Accede al chat y evidencias de cada estudiante para análisis posterior.
            </p>
            {metrics.lab_sessions.length === 0 ? (
              <p className="muted">No hay sesiones de laboratorio.</p>
            ) : (
              <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Estudiante</th>
                      <th>Laboratorio</th>
                      <th>Estado</th>
                      <th>Mensajes</th>
                      <th>Evidencias</th>
                      <th>Duración</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labSessionsPagination.pageItems.map((row) => (
                      <tr key={row.session_id}>
                        <td>
                          <strong>{row.student_name}</strong>
                          <br />
                          <span className="muted">{row.student_email}</span>
                        </td>
                        <td>{row.lab_title}</td>
                        <td>{row.status}</td>
                        <td>{row.student_message_count}</td>
                        <td>{row.evidence_count}</td>
                        <td>
                          {row.duration_minutes != null
                            ? `${row.duration_minutes} min`
                            : "—"}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            onClick={() => onViewLabSession(row.session_id)}
                          >
                            Ver chat y evidencias
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={labSessionsPagination.page}
                totalPages={labSessionsPagination.totalPages}
                totalItems={labSessionsPagination.totalItems}
                pageSize={labSessionsPagination.pageSize}
                onPageChange={labSessionsPagination.setPage}
              />
              </>
            )}
          </section>

          <section className="card">
            <h3>Evaluaciones</h3>
            {metrics.evaluation_attempts.length === 0 ? (
              <p className="muted">No hay intentos de evaluación.</p>
            ) : (
              <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Estudiante</th>
                      <th>Evaluación</th>
                      <th>Tema</th>
                      <th>Estado</th>
                      <th>Puntuación</th>
                      <th>Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluationAttemptsPagination.pageItems.map((row) => (
                      <tr key={row.attempt_id}>
                        <td>{row.student_name}</td>
                        <td>{row.evaluation_title}</td>
                        <td>{row.topic}</td>
                        <td>{row.status}</td>
                        <td>
                          {row.score != null
                            ? `${row.score}% (${row.correct_count}/${row.total_questions})`
                            : "—"}
                        </td>
                        <td>
                          {row.completed_at
                            ? new Date(row.completed_at).toLocaleString()
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={evaluationAttemptsPagination.page}
                totalPages={evaluationAttemptsPagination.totalPages}
                totalItems={evaluationAttemptsPagination.totalItems}
                pageSize={evaluationAttemptsPagination.pageSize}
                onPageChange={evaluationAttemptsPagination.setPage}
              />
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
