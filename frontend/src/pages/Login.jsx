import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AboutSection from "../components/AboutSection";

export default function Login() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [securityQuestions, setSecurityQuestions] = useState([]);

  const [form, setForm] = useState({
    nombre: "",
    email: "",
    password: "",
    password2: "",
    role: "student",
    security_question: "",
    security_answer: "",
  });

  const [forgotStep, setForgotStep] = useState(1);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotQuestion, setForgotQuestion] = useState("");
  const [forgotAnswer, setForgotAnswer] = useState("");
  const [forgotPassword, setForgotPassword] = useState("");
  const [forgotPassword2, setForgotPassword2] = useState("");

  useEffect(() => {
    if (mode === "register" && securityQuestions.length === 0) {
      api
        .getSecurityQuestions()
        .then((data) => {
          const questions = data.questions || [];
          setSecurityQuestions(questions);
          if (questions.length > 0) {
            setForm((prev) => ({
              ...prev,
              security_question: prev.security_question || questions[0],
            }));
          }
        })
        .catch(() => {});
    }
  }, [mode, securityQuestions.length]);

  if (user) {
    return (
      <Navigate to={user.role === "teacher" ? "/docente" : "/estudiante"} replace />
    );
  }

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setError("");
    setSuccess("");
    if (nextMode !== "forgot") {
      setForgotStep(1);
      setForgotEmail("");
      setForgotQuestion("");
      setForgotAnswer("");
      setForgotPassword("");
      setForgotPassword2("");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "login") {
        await login(form.email, form.password);
      } else {
        if (form.password !== form.password2) {
          throw new Error("Las contraseñas no coinciden.");
        }
        if (form.password.length < 6) {
          throw new Error("La contraseña debe tener al menos 6 caracteres.");
        }
        if (!form.security_question || !form.security_answer.trim()) {
          throw new Error("Selecciona una pregunta de seguridad y escribe tu respuesta.");
        }
        await register({
          nombre: form.nombre,
          email: form.email,
          password: form.password,
          role: form.role,
          security_question: form.security_question,
          security_answer: form.security_answer,
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotLookup = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const data = await api.forgotPasswordLookup(forgotEmail);
      setForgotQuestion(data.security_question);
      setForgotStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotReset = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (forgotPassword !== forgotPassword2) {
        throw new Error("Las contraseñas no coinciden.");
      }
      if (forgotPassword.length < 6) {
        throw new Error("La contraseña debe tener al menos 6 caracteres.");
      }

      const data = await api.forgotPasswordReset({
        email: forgotEmail,
        security_answer: forgotAnswer,
        new_password: forgotPassword,
        confirm_password: forgotPassword2,
      });

      setSuccess(data.message || "Contraseña actualizada.");
      setForm((prev) => ({ ...prev, email: forgotEmail, password: "" }));
      switchMode("login");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-layout">
        <div className="auth-card">
          <div className="auth-brand">
            <div className="brand-mark" aria-hidden="true">
              GAIA
            </div>
            <div>
              <h1>Profesor IA</h1>
              <p className="subtitle">
                Plataforma de evaluación con inteligencia artificial
              </p>
            </div>
          </div>

          {mode !== "forgot" ? (
            <div className="tabs">
              <button
                type="button"
                className={mode === "login" ? "tab active" : "tab"}
                onClick={() => switchMode("login")}
              >
                Iniciar sesión
              </button>
              <button
                type="button"
                className={mode === "register" ? "tab active" : "tab"}
                onClick={() => switchMode("register")}
              >
                Registrarse
              </button>
            </div>
          ) : (
            <h3 className="auth-section-title">Recuperar contraseña</h3>
          )}

          {mode === "forgot" ? (
            forgotStep === 1 ? (
              <form onSubmit={handleForgotLookup} className="form">
                <p className="muted">
                  Ingresa tu correo para ver tu pregunta de seguridad.
                </p>
                <label>
                  Correo electrónico
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    required
                  />
                </label>
                {error && <p className="error">{error}</p>}
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? "Buscando..." : "Continuar"}
                </button>
                <button
                  type="button"
                  className="btn-ghost auth-back-link"
                  onClick={() => switchMode("login")}
                >
                  Volver al inicio de sesión
                </button>
              </form>
            ) : (
              <form onSubmit={handleForgotReset} className="form">
                <p className="muted">
                  Responde tu pregunta de seguridad y elige una nueva contraseña.
                </p>
                <label>
                  Pregunta de seguridad
                  <input value={forgotQuestion} readOnly />
                </label>
                <label>
                  Respuesta
                  <input
                    value={forgotAnswer}
                    onChange={(e) => setForgotAnswer(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Nueva contraseña
                  <input
                    type="password"
                    value={forgotPassword}
                    onChange={(e) => setForgotPassword(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Confirmar contraseña
                  <input
                    type="password"
                    value={forgotPassword2}
                    onChange={(e) => setForgotPassword2(e.target.value)}
                    required
                  />
                </label>
                {error && <p className="error">{error}</p>}
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? "Guardando..." : "Restablecer contraseña"}
                </button>
                <button
                  type="button"
                  className="btn-ghost auth-back-link"
                  onClick={() => {
                    setForgotStep(1);
                    setError("");
                  }}
                >
                  Cambiar correo
                </button>
              </form>
            )
          ) : (
            <form onSubmit={handleSubmit} className="form">
              {mode === "register" && (
                <>
                  <label>
                    Nombre completo
                    <input
                      value={form.nombre}
                      onChange={(e) => update("nombre", e.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Tipo de cuenta
                    <select
                      value={form.role}
                      onChange={(e) => update("role", e.target.value)}
                    >
                      <option value="student">Estudiante</option>
                      <option value="teacher">Docente</option>
                    </select>
                  </label>
                  <label>
                    Pregunta de seguridad
                    <select
                      value={form.security_question}
                      onChange={(e) => update("security_question", e.target.value)}
                      required
                    >
                      {securityQuestions.map((question) => (
                        <option key={question} value={question}>
                          {question}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Respuesta de seguridad
                    <input
                      value={form.security_answer}
                      onChange={(e) => update("security_answer", e.target.value)}
                      placeholder="Respuesta personal (para recuperar contraseña)"
                      required
                    />
                  </label>
                </>
              )}

              <label>
                Correo electrónico
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  required
                />
              </label>

              <label>
                Contraseña
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => update("password", e.target.value)}
                  required
                />
              </label>

              {mode === "register" && (
                <label>
                  Confirmar contraseña
                  <input
                    type="password"
                    value={form.password2}
                    onChange={(e) => update("password2", e.target.value)}
                    required
                  />
                </label>
              )}

              {mode === "login" && (
                <button
                  type="button"
                  className="btn-ghost auth-back-link align-left"
                  onClick={() => switchMode("forgot")}
                >
                  ¿Olvidaste tu contraseña?
                </button>
              )}

              {error && <p className="error">{error}</p>}
              {success && <p className="success">{success}</p>}

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading
                  ? "Procesando..."
                  : mode === "login"
                    ? "Entrar"
                    : "Crear cuenta"}
              </button>
            </form>
          )}
        </div>
        <AboutSection />
      </div>
    </div>
  );
}
