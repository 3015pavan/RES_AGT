"use client";

import { FormEvent, useState } from "react";

import { generateReport } from "@/lib/api-client";
import type { ReportPayload } from "@/lib/types";

export function ReportPanel() {
  const [reportType, setReportType] = useState<ReportPayload["report_type"]>("student");
  const [usn, setUsn] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const filters: Record<string, string> = {};
    if (usn.trim()) {
      filters.usn = usn.trim();
    }
    if (subject.trim()) {
      filters.subject = subject.trim();
    }

    try {
      const payload: ReportPayload = {
        report_type: reportType,
        filters,
      };
      const data = await generateReport(payload);
      setResult(data);
    } catch {
      setError("Server error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[360px_1fr]">
      <form onSubmit={onSubmit} className="card space-y-3 p-4">
        <h2 className="text-base font-semibold">Generate Report</h2>

        <label className="block text-sm">
          <span className="mb-1 block">Report Type</span>
          <select className="input" value={reportType} onChange={(e) => setReportType(e.target.value as ReportPayload["report_type"])}>
            <option value="student">Student</option>
            <option value="class">Class</option>
            <option value="subject">Subject</option>
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block">USN (optional)</span>
          <input className="input" value={usn} onChange={(e) => setUsn(e.target.value)} placeholder="1MS21CS001" />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block">Subject (optional)</span>
          <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="physics" />
        </label>

        <button className="btn-primary w-full" type="submit" disabled={loading}>
          {loading ? "Generating..." : "Generate"}
        </button>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </form>

      <section className="card p-4">
        <h3 className="mb-2 text-sm font-semibold">Result</h3>
        {!result ? (
          <p className="text-sm text-gray-600">Run a report to see results.</p>
        ) : (
          <pre className="overflow-auto rounded-xl bg-[#f8f8f2] p-3 text-xs">{JSON.stringify(result, null, 2)}</pre>
        )}
      </section>
    </div>
  );
}
