import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Teacher from "./pages/Teacher";
import Student from "./pages/Student";

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading">Cargando...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "teacher" ? "/docente" : "/estudiante"} replace />;
  }

  return children;
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading">Cargando...</div>;
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          user ? (
            <Navigate to={user.role === "teacher" ? "/docente" : "/estudiante"} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="/login" element={<Login />} />
      <Route
        path="/docente"
        element={
          <ProtectedRoute role="teacher">
            <Layout>
              <Teacher />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/estudiante"
        element={
          <ProtectedRoute role="student">
            <Layout>
              <Student />
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
