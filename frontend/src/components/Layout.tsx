import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router";

import type { UserRole } from "../api/client.js";
import { useAuth } from "../lib/auth-context.js";

/* ------------------------------------------------------------------ */
/*  Navigation items per role                                          */
/* ------------------------------------------------------------------ */

type NavItem = { label: string; to: string };

const NAV: Record<UserRole, NavItem[]> = {
  ADMIN: [
    { label: "Dashboard", to: "/" },
    { label: "Customers", to: "/customers" },
    { label: "Subscriptions", to: "/subscriptions" },
    { label: "Quotation Templates", to: "/quotation-templates" },
    { label: "Invoices", to: "/invoices" },
    { label: "Payments", to: "/payments" },
    { label: "Catalog", to: "/catalog" },
    { label: "Plans", to: "/plans" },
    { label: "Audit Log", to: "/audit-log" },
    { label: "Email Outbox", to: "/email-outbox" },
    { label: "Staff Management", to: "/staff" },
  ],
  STAFF: [
    { label: "Dashboard", to: "/" },
    { label: "Customers", to: "/customers" },
    { label: "Subscriptions", to: "/subscriptions" },
    { label: "Invoices", to: "/invoices" },
    { label: "Payments", to: "/payments" },
  ],
  CUSTOMER: [
    { label: "My Subscriptions", to: "/my/subscriptions" },
    { label: "My Invoices", to: "/my/invoices" },
    { label: "My Profile", to: "/my/profile" },
  ],
};

const ROLE_COLOR: Record<UserRole, string> = {
  ADMIN: "bg-red-100 text-red-700",
  STAFF: "bg-blue-100 text-blue-700",
  CUSTOMER: "bg-emerald-100 text-emerald-700",
};

/* ------------------------------------------------------------------ */
/*  Layout component                                                   */
/* ------------------------------------------------------------------ */

export default function Layout() {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!user) return null;

  const items = NAV[user.role] ?? [];

  const linkClasses = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? "bg-indigo-50 text-indigo-700"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    }`;

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform md:static md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center border-b border-slate-200 px-4">
          <Link to="/" className="text-lg font-bold text-indigo-600">
            Brightloop
          </Link>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main navigation">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={linkClasses}
              onClick={() => setSidebarOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
          <button
            type="button"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            {/* Hamburger icon */}
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          <div className="flex-1" />

          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-slate-700">
              {user.full_name}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${ROLE_COLOR[user.role]}`}
            >
              {user.role}
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            >
              Log out
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
