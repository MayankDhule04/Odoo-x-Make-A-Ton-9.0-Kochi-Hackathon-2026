import { useAuth } from "../lib/auth-context.js";

const KPIS = [
  { label: "Active Subscriptions", value: "—" },
  { label: "Revenue", value: "—" },
  { label: "Outstanding", value: "—" },
  { label: "Overdue", value: "—" },
];

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Welcome, {user?.full_name}
        </h1>
        <p className="mt-1 text-sm text-slate-500">Role: {user?.role}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {KPIS.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"
          >
            <p className="text-sm font-medium text-slate-500">{kpi.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {kpi.value}
            </p>
          </div>
        ))}
      </div>

      <p className="text-sm text-slate-400">
        Dashboard data will be populated by Member 4
      </p>
    </div>
  );
}
