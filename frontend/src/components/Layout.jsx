import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import AboutSection from "./AboutSection";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [showAbout, setShowAbout] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [user?.id]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">
              GAIA
            </div>
            <div>
              <h1>Profesor IA</h1>
              <p className="brand-subtitle">Universidad Nacional de Colombia</p>
            </div>
          </div>

          <button
            type="button"
            className="header-menu-toggle"
            aria-expanded={menuOpen}
            aria-label="Abrir menú"
            onClick={() => setMenuOpen((current) => !current)}
          >
            ☰
          </button>

          <div className={`header-user ${menuOpen ? "open" : ""}`}>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setShowAbout((current) => !current);
                setMenuOpen(false);
              }}
            >
              Acerca de
            </button>
            <span className="user-name">{user.nombre}</span>
            <span className="badge">
              {user.role === "teacher" ? "Docente" : "Estudiante"}
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                logout();
                setMenuOpen(false);
              }}
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      {showAbout && (
        <div className="about-banner">
          <AboutSection />
        </div>
      )}

      <main className="main">{children}</main>
      <AboutSection compact />
    </div>
  );
}
