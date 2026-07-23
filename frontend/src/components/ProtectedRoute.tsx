import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role, UserOut } from "../api/types";
import { homePathForRole } from "../lib/roles";
import { Spinner } from "./ui/Feedback";

interface ProtectedRouteProps {
  children: ReactNode;
  // Simple exact-role match (most routes) - mutually exclusive with `allow`.
  role?: Role;
  // Predicate-based access for routes multiple roles can reach (e.g.
  // Product & CX pages, reachable by PRODUCT_CX accounts and super-admins
  // alike) - see lib/roles.ts's canAccessProductCx for the canonical example.
  allow?: (identity: UserOut) => boolean;
}

export function ProtectedRoute({ role, allow, children }: ProtectedRouteProps) {
  const { token, identity, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner label="Loading..." />
      </div>
    );
  }

  if (!token || !identity) return <Navigate to="/login" replace />;

  const isAllowed = allow ? allow(identity) : identity.role === role;
  if (!isAllowed) return <Navigate to={homePathForRole(identity.role)} replace />;

  return <>{children}</>;
}
