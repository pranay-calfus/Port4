import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../api/types";
import { Spinner } from "./ui/Feedback";

export function ProtectedRoute({ role, children }: { role: Role; children: ReactNode }) {
  const { token, identity, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner label="Loading..." />
      </div>
    );
  }

  if (!token || !identity) return <Navigate to="/login" replace />;
  if (identity.role !== role) return <Navigate to={identity.role === "ADMIN" ? "/admin" : "/"} replace />;

  return <>{children}</>;
}
