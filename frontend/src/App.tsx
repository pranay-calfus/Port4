import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Header } from "./components/Header";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { SurveyBubble } from "./components/SurveyBubble";
import { Spinner } from "./components/ui/Feedback";
import { homePathForRole } from "./lib/roles";
import { LoginPage } from "./pages/LoginPage";
import { CustomerHomePage } from "./pages/CustomerHomePage";
import { CustomerTicketPage } from "./pages/CustomerTicketPage";
import { AdminHomePage } from "./pages/AdminHomePage";
import { AdminTicketPage } from "./pages/AdminTicketPage";
import { AdminTeamPage } from "./pages/AdminTeamPage";
import { ProductCxDashboardPage } from "./pages/ProductCxDashboardPage";
import { SurveyManagementPage } from "./pages/SurveyManagementPage";

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
    return <Navigate to={homePathForRole(identity.role)} replace />;
  }
  return <LoginPage />;
}

export default function App() {
  const { identity } = useAuth();

  return (
    <div className="min-h-screen bg-surface text-ink">
      <Header />
      {identity?.role === "USER" && <SurveyBubble />}
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
        <Route
          path="/product-cx"
          element={
            <ProtectedRoute role="PRODUCT_CX">
              <ProductCxDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/product-cx/surveys"
          element={
            <ProtectedRoute role="PRODUCT_CX">
              <SurveyManagementPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
