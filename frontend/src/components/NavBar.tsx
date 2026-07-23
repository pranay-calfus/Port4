import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { isSuperAdmin } from "../lib/roles";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm ${isActive ? "font-semibold text-ink" : "text-ink-muted hover:text-ink"}`;

function NavSection({ label, links }: { label: string; links: { to: string; text: string }[] }) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</span>
      {links.map((link) => (
        <NavLink key={link.to} to={link.to} className={linkClass}>
          {link.text}
        </NavLink>
      ))}
    </div>
  );
}

const SUPPORT_OPS_LINKS = [
  { to: "/admin/tickets", text: "Tickets" },
  { to: "/admin/analytics", text: "Ticket Analytics" },
];

const PRODUCT_CX_LINKS = [
  { to: "/product-cx/feedback", text: "Feedback" },
  { to: "/product-cx/surveys", text: "Surveys" },
  { to: "/product-cx/analytics", text: "Feedback Analytics" },
];

/** Sectioned navigation clearly separating Support Operations from
 * Product & CX, per role: department-scoped admins see Support Operations
 * only, Product & CX accounts see Product & CX only, and super-admins see
 * both (full access to every module). Renders nothing for customers (USER)
 * - their navigation is the in-page tabs on the home page.
 */
export function NavBar() {
  const { identity } = useAuth();
  if (!identity) return null;

  const showSupportOps = identity.role === "ADMIN";
  const showProductCx = identity.role === "PRODUCT_CX" || isSuperAdmin(identity);

  if (!showSupportOps && !showProductCx) return null;

  return (
    <nav className="flex flex-wrap items-center gap-x-8 gap-y-2 border-b border-surface-border px-6 py-3">
      {showSupportOps && <NavSection label="Support Operations" links={SUPPORT_OPS_LINKS} />}
      {showProductCx && <NavSection label="Product & CX" links={PRODUCT_CX_LINKS} />}
    </nav>
  );
}
