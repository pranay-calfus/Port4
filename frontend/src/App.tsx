import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Header } from "./components/Header";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Spinner } from "./components/ui/Feedback";
import { LoginPage } from "./pages/LoginPage";
import { CustomerHomePage } from "./pages/CustomerHomePage";
import { CustomerTicketPage } from "./pages/CustomerTicketPage";
import { AdminHomePage } from "./pages/AdminHomePage";
import { AdminTicketPage } from "./pages/AdminTicketPage";
import { AdminTeamPage } from "./pages/AdminTeamPage";

function LoginRoute() {
  const { token, identity, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Spinner label="Loading..." />
      </div>
    );
  }
  if (token && identity) {
    return <Navigate to={identity.role === "ADMIN" ? "/admin" : "/"} replace />;
  }
  return <LoginPage />;
}

export default function App() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <Header />
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route
          path="/"
          element={
            <ProtectedRoute role="USER">
              <CustomerHomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tickets/:ticketId"
          element={
            <ProtectedRoute role="USER">
              <CustomerTicketPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute role="ADMIN">
              <AdminHomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/tickets/:ticketId"
          element={
            <ProtectedRoute role="ADMIN">
              <AdminTicketPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/team"
          element={
            <ProtectedRoute role="ADMIN">
              <AdminTeamPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
