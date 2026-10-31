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
import CatalogPage from "./features/catalog/CatalogPage.js";
import PlansPage from "./features/catalog/PlansPage.js";
import InvoiceDetailPage from "./features/invoices/InvoiceDetailPage.js";
import InvoicesPage from "./features/invoices/InvoicesPage.js";
import QuotationTemplatesPage from "./features/subscriptions/QuotationTemplatesPage.js";
import SubscriptionDetailPage from "./features/subscriptions/SubscriptionDetailPage.js";
import SubscriptionsPage from "./features/subscriptions/SubscriptionsPage.js";
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
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <SubscriptionsPage />
            </RequireRole>
          }
        />
        <Route
          path="subscriptions/:id"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <SubscriptionDetailPage />
            </RequireRole>
          }
        />
        <Route
          path="quotation-templates"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <QuotationTemplatesPage />
            </RequireRole>
          }
        />
        <Route
          path="invoices"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <InvoicesPage />
            </RequireRole>
          }
        />
        <Route
          path="invoices/:id"
          element={
            <RequireRole roles={["ADMIN", "STAFF"]}>
              <InvoiceDetailPage />
            </RequireRole>
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
              <CatalogPage />
            </RequireRole>
          }
        />
        <Route
          path="plans"
          element={
            <RequireRole roles={["ADMIN"]}>
              <PlansPage />
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
              <InvoicesPage customerMode={true} />
            </RequireRole>
          }
        />
        <Route
          path="my/invoices/:id"
          element={
            <RequireRole roles={["CUSTOMER"]}>
              <InvoiceDetailPage customerMode={true} />
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
