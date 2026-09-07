export default function AboutSection({ compact = false }) {
  if (compact) {
    return (
      <footer className="about-footer">
        <div className="about-footer-inner">
          <div>
            <strong>Grupo GAIA</strong>
            <span className="about-divider">·</span>
            <span className="muted">
              Ambientes Inteligentes Adaptativos — Universidad Nacional de Colombia
            </span>
          </div>
          <p className="about-tagline muted">
            Plataforma educativa con IA para docentes y estudiantes
          </p>
        </div>
      </footer>
    );
  }

  return (
    <section className="about-section card">
      <div className="about-badge">Acerca de</div>
      <h3>Grupo GAIA</h3>
      <p className="about-lead">
        <strong>Grupo de Ambientes Inteligentes Adaptativos</strong> de la{" "}
        <strong>Universidad Nacional de Colombia</strong>.
      </p>
      <p className="muted">
        Desarrollamos herramientas que apoyan el aprendizaje con inteligencia
        artificial: evaluaciones, laboratorios virtuales, métricas docentes y
        análisis de conversaciones.
      </p>
      <div className="about-meta">
        <span className="about-pill">Profesor IA</span>
        <span className="about-pill">UNAL</span>
        <span className="about-pill">RAG + Ollama</span>
      </div>
    </section>
  );
}
