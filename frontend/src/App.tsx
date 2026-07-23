import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Header } from "./components/Header";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { SurveyBubble } from "./components/SurveyBubble";
import { Spinner } from "./components/ui/Feedback";
import { canAccessProductCx, homePathForRole } from "./lib/roles";
import { LoginPage } from "./pages/LoginPage";
import { CustomerHomePage } from "./pages/CustomerHomePage";
import { CustomerTicketPage } from "./pages/CustomerTicketPage";
import { AdminAnalyticsPage } from "./pages/AdminAnalyticsPage";
import { AdminTicketsPage } from "./pages/AdminTicketsPage";
import { AdminTicketPage } from "./pages/AdminTicketPage";
import { AdminTeamPage } from "./pages/AdminTeamPage";
import { ProductCxAnalyticsPage } from "./pages/ProductCxAnalyticsPage";
import { ProductCxFeedbackPage } from "./pages/ProductCxFeedbackPage";
import { ProductCxSurveysPage } from "./pages/ProductCxSurveysPage";
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
        <Route path="/admin" element={<Navigate to="/admin/analytics" replace />} />
        <Route
          path="/admin/tickets"
          element={
            <ProtectedRoute role="ADMIN">
              <AdminTicketsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/analytics"
          element={
            <ProtectedRoute role="ADMIN">
              <AdminAnalyticsPage />
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
        <Route path="/product-cx" element={<Navigate to="/product-cx/analytics" replace />} />
        <Route
          path="/product-cx/feedback"
          element={
            <ProtectedRoute allow={canAccessProductCx}>
              <ProductCxFeedbackPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/product-cx/analytics"
          element={
            <ProtectedRoute allow={canAccessProductCx}>
              <ProductCxAnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/product-cx/surveys"
          element={
            <ProtectedRoute allow={canAccessProductCx}>
              <ProductCxSurveysPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/product-cx/surveys/manage"
          element={
            <ProtectedRoute allow={canAccessProductCx}>
              <SurveyManagementPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
