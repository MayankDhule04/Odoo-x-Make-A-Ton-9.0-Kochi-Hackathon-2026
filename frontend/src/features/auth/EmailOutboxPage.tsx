import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { api } from "../../api/client.js";
import type { EmailOutboxEntry, Page } from "../../api/client.js";

const PAGE_SIZE = 25;

export default function EmailOutboxPage() {
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["email-outbox", page],
    queryFn: () =>
      api.get<Page<EmailOutboxEntry>>("/api/email-outbox", {
        page: String(page),
        page_size: String(PAGE_SIZE),
      }),
  });

  const columns = useMemo<ColumnDef<EmailOutboxEntry>[]>(
    () => [
      { accessorKey: "to_email", header: "To" },
      { accessorKey: "subject", header: "Subject" },
      {
        accessorKey: "body",
        header: "Body",
        cell: ({ row }) => {
          const body = row.original.body;
          const isExpanded = expandedId === row.original.id;
          return (
            <div>
              <span>
                {isExpanded
                  ? body
                  : body.length > 80
                    ? `${body.slice(0, 80)}…`
                    : body}
              </span>
              {body.length > 80 && (
                <button
                  type="button"
                  className="ml-2 text-xs text-indigo-600 hover:text-indigo-500"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedId(isExpanded ? null : row.original.id);
                  }}
                >
                  {isExpanded ? "collapse" : "expand"}
                </button>
              )}
            </div>
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
    [expandedId],
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
      <h1 className="text-2xl font-semibold text-slate-900">
        Email Outbox{" "}
        <span className="text-sm font-normal text-slate-400">(dev only)</span>
      </h1>

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">
            Failed to load email outbox.
          </p>
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
                      No emails in outbox
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
