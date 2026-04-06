"use client";

import { useEffect, useState } from "react";

import { fetchDocuments } from "@/lib/api-client";
import type { DocumentRow } from "@/lib/types";

export function DocumentsTable() {
  const [rows, setRows] = useState<DocumentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchDocuments();
        setRows(data);
      } catch {
        setError("Server error");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (loading) {
    return <div className="card p-4 text-sm text-gray-600">Loading documents...</div>;
  }

  if (error) {
    return <div className="card p-4 text-sm text-red-600">{error}</div>;
  }

  if (rows.length === 0) {
    return <div className="card p-4 text-sm text-gray-600">NO DATA AVAILABLE</div>;
  }

  return (
    <div className="card overflow-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-accentSoft text-left">
          <tr>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Source</th>
            <th className="px-3 py-2">MIME</th>
            <th className="px-3 py-2">Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-stroke">
              <td className="px-3 py-2">{row.file_name}</td>
              <td className="px-3 py-2">{row.source_type}</td>
              <td className="px-3 py-2">{row.mime_type}</td>
              <td className="px-3 py-2">{new Date(row.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
