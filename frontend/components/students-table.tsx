"use client";

import { useEffect, useState } from "react";

import { fetchStudents } from "@/lib/api-client";
import type { StudentRow } from "@/lib/types";

export function StudentsTable() {
  const [rows, setRows] = useState<StudentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchStudents();
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
    return <div className="card p-4 text-sm text-gray-600">Loading students...</div>;
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
            <th className="px-3 py-2">USN</th>
            <th className="px-3 py-2">Name</th>
            <th className="px-3 py-2">Semester</th>
            <th className="px-3 py-2">Section</th>
            <th className="px-3 py-2">SGPA</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-stroke">
              <td className="px-3 py-2 font-mono">{row.usn}</td>
              <td className="px-3 py-2">{row.student_name ?? "-"}</td>
              <td className="px-3 py-2">{row.semester ?? "-"}</td>
              <td className="px-3 py-2">{row.section ?? "-"}</td>
              <td className="px-3 py-2">{row.sgpa ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
