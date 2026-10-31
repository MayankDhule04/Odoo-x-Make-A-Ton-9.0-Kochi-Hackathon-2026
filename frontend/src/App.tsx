import { Route, Routes } from "react-router";

import Layout from "./components/Layout.js";
import AuditLogPage from "./features/auth/AuditLogPage.js";
import CreateStaffPage from "./features/auth/CreateStaffPage.js";
import CustomerDetailPage from "./features/auth/CustomerDetailPage.js";
import CustomerListPage from "./features/auth/CustomerListPage.js";
import CustomerProfilePage from "./features/auth/CustomerProfilePage.js";
import EmailOutboxPage from "./features/auth/EmailOutboxPage.js";
import ForgotPasswordPage from "./features/auth/ForgotPasswordPage.js";
import LoginPage from "./features/auth/LoginPage.js";
import ResetPasswordPage from "./features/auth/ResetPasswordPage.js";
import SignupPage from "./features/auth/SignupPage.js";
import { RequireAuth, RequireGuest, RequireRole } from "./lib/require-auth.js";
import DashboardPage from "./pages/DashboardPage.js";
import NotFoundPage from "./pages/NotFoundPage.js";
import PlaceholderPage from "./pages/PlaceholderPage.js";

export default function App() {
  return (
    <Routes>
      {/* Public / guest-only routes */}
      <Route
        path="/login"
        element={
          <RequireGuest>
            <LoginPage />
          </RequireGuest>
        }
      />
      <Route
        path="/signup"
        element={
          <RequireGuest>
            <SignupPage />
          </RequireGuest>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <RequireGuest>
            <ForgotPasswordPage />
          </RequireGuest>
        }
      />
      <Route
        path="/reset-password"
        element={
          <RequireGuest>
            <ResetPasswordPage />
          </RequireGuest>
        }
      />

      {/* Protected routes inside the shell layout */}
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />

        {/* Staff / Admin */}
        <Route
          path="customers"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <CustomerListPage />
            </RequireRole>
          }
        />
        <Route
          path="customers/:id"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <CustomerDetailPage />
            </RequireRole>
          }
        />

        {/* Placeholders – to be built by other members */}
        <Route
          path="subscriptions"
          element={
            <PlaceholderPage
              title="Subscriptions"
              description="Subscription management will be built by another team member."
            />
          }
        />
        <Route
          path="invoices"
          element={
            <PlaceholderPage
              title="Invoices"
              description="Invoice management will be built by another team member."
            />
          }
        />
        <Route
          path="payments"
          element={
            <PlaceholderPage
              title="Payments"
              description="Payment management will be built by another team member."
            />
          }
        />

        {/* Admin only */}
        <Route
          path="catalog"
          element={
            <RequireRole roles={["ADMIN"]}>
              <PlaceholderPage
                title="Catalog"
                description="Catalog management will be built by another team member."
              />
            </RequireRole>
          }
        />
        <Route
          path="plans"
          element={
            <RequireRole roles={["ADMIN"]}>
              <PlaceholderPage
                title="Plans"
                description="Plan management will be built by another team member."
              />
            </RequireRole>
          }
        />
        <Route
          path="audit-log"
          element={
            <RequireRole roles={["ADMIN"]}>
              <AuditLogPage />
            </RequireRole>
          }
        />
        <Route
          path="email-outbox"
          element={
            <RequireRole roles={["ADMIN"]}>
              <EmailOutboxPage />
            </RequireRole>
          }
        />
        <Route
          path="staff"
          element={
            <RequireRole roles={["ADMIN"]}>
              <CreateStaffPage />
            </RequireRole>
          }
        />

        {/* Customer self-service */}
        <Route
          path="my/subscriptions"
          element={
            <RequireRole roles={["CUSTOMER"]}>
              <PlaceholderPage
                title="My Subscriptions"
                description="Your subscription overview will appear here."
              />
            </RequireRole>
          }
        />
        <Route
          path="my/invoices"
          element={
            <RequireRole roles={["CUSTOMER"]}>
              <PlaceholderPage
                title="My Invoices"
                description="Your invoices will appear here."
              />
            </RequireRole>
          }
        />
        <Route
          path="my/profile"
          element={
            <RequireRole roles={["CUSTOMER"]}>
              <CustomerProfilePage />
            </RequireRole>
          }
        />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
