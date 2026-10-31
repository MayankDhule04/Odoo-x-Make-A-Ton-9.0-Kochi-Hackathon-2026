import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { api } from "../../api/client.js";
import type { AuditLogEntry, Page } from "../../api/client.js";

const PAGE_SIZE = 25;

export default function AuditLogPage() {
  const [page, setPage] = useState(1);
  const [entityType, setEntityType] = useState("");
  const [actorId, setActorId] = useState("");
  const [after, setAfter] = useState("");
  const [before, setBefore] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-log", page, entityType, actorId, after, before],
    queryFn: () => {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(PAGE_SIZE),
      };
      if (entityType) params.entity_type = entityType;
      if (actorId) params.actor_id = actorId;
      if (after) params.after = after;
      if (before) params.before = before;
      return api.get<Page<AuditLogEntry>>("/api/audit-log", params);
    },
  });

  const columns = useMemo<ColumnDef<AuditLogEntry>[]>(
    () => [
      { accessorKey: "id", header: "ID", size: 60 },
      { accessorKey: "actor_id", header: "Actor", size: 80 },
      { accessorKey: "entity_type", header: "Entity Type" },
      { accessorKey: "entity_id", header: "Entity ID", size: 80 },
      { accessorKey: "action", header: "Action" },
      {
        accessorKey: "changes",
        header: "Changes",
        cell: ({ getValue }) => {
          const v = getValue<string | null>();
          if (!v) return <span className="text-slate-400">—</span>;
          return (
            <span title={v}>
              {v.length > 60 ? `${v.slice(0, 60)}…` : v}
            </span>
          );
        },
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ getValue }) =>
          new Date(getValue<string>()).toLocaleString(),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: data?.pages ?? -1,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">Audit Log</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
        <input
          type="text"
          placeholder="Entity type"
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
        />
        <input
          type="number"
          placeholder="Actor ID"
          value={actorId}
          onChange={(e) => {
            setActorId(e.target.value);
            setPage(1);
          }}
          className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
        />
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          After
          <input
            type="datetime-local"
            value={after}
            onChange={(e) => {
              setAfter(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
          />
        </label>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          Before
          <input
            type="datetime-local"
            value={before}
            onChange={(e) => {
              setBefore(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
          />
        </label>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load audit log.</p>
        ) : (
          <>
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((header) => (
                      <th key={header.id} className="px-4 py-3">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-100">
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 text-slate-700">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
                {data?.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      className="px-4 py-8 text-center text-slate-400"
                    >
                      No entries found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm">
              <span className="text-slate-500">
                Page {data?.page ?? 1} of {data?.pages ?? 1} ({data?.total ?? 0}{" "}
                total)
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={page >= (data?.pages ?? 1)}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
