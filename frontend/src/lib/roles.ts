import type { Role } from "../api/types";

export function homePathForRole(role: Role): string {
  if (role === "ADMIN") return "/admin";
  if (role === "PRODUCT_CX") return "/product-cx";
  return "/";
}
