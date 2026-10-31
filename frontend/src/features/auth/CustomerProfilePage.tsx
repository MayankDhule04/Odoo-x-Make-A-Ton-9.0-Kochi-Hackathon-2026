import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client.js";
import type { Customer } from "../../api/client.js";

export default function CustomerProfilePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["customer-me"],
    queryFn: () => api.get<Customer>("/api/customers/me"),
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading profile…</p>;
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">
        Failed to load your profile.
      </div>
    );
  }

  const rows: Array<{ label: string; value: string }> = [
    { label: "Name", value: data.name },
    { label: "Email", value: data.email },
    { label: "Phone", value: data.phone ?? "—" },
    { label: "Billing Address", value: data.billing_address ?? "—" },
    { label: "Status", value: data.is_active ? "Active" : "Inactive" },
  ];

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">My Profile</h1>

      <div className="divide-y divide-slate-100 rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between px-5 py-3">
            <span className="text-sm font-medium text-slate-500">
              {row.label}
            </span>
            <span className="text-sm text-slate-900">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
