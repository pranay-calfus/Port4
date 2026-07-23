import type { Role, UserOut } from "../api/types";

export function homePathForRole(role: Role): string {
  if (role === "ADMIN") return "/admin/analytics";
  if (role === "PRODUCT_CX") return "/product-cx/analytics";
  return "/";
}

/** A super-admin is an ADMIN with no department - the one place this
 * check lives, reused by ProfileMenu, NavBar, and ProtectedRoute's
 * predicate-based routes (previously computed independently in
 * ProfileMenu.tsx and the old AdminHomePage.tsx).
 */
export function isSuperAdmin(identity: UserOut | null | undefined): boolean {
  return identity?.role === "ADMIN" && identity.department == null;
}

/** Whether this identity can reach the Product & CX module - PRODUCT_CX
 * accounts, plus super-admins (who have full access to every module).
 */
export function canAccessProductCx(identity: UserOut | null | undefined): boolean {
  return identity?.role === "PRODUCT_CX" || isSuperAdmin(identity);
}
