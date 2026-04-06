"use client";

import { useMemo, useState } from "react";

import { uploadFile } from "@/lib/api-client";

const allowedExtensions = ["csv", "xlsx", "pdf"];

export function UploadPanel() {
  const [selected, setSelected] = useState<File | null>(null);
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const isAllowed = useMemo(() => {
    if (!selected) {
      return true;
    }
    const ext = selected.name.split(".").pop()?.toLowerCase() ?? "";
    return allowedExtensions.includes(ext);
  }, [selected]);

  async function onUpload() {
    if (!selected || !isAllowed || loading) {
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const data = await uploadFile(selected);
      setMessage(`Uploaded. Rows: ${data.rows_ingested}, Documents: ${data.documents_created}`);
      setSelected(null);
    } catch {
      setMessage("Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card p-3">
      <h3 className="mb-2 text-sm font-semibold">File Upload</h3>
      <label htmlFor="upload-file" className="mb-1 block text-xs text-gray-600">CSV, XLSX, or PDF</label>
      <input
        id="upload-file"
        className="input text-sm"
        type="file"
        accept=".csv,.xlsx,.pdf"
        onChange={(event) => setSelected(event.target.files?.[0] ?? null)}
      />
      {!isAllowed ? <p className="mt-2 text-xs text-red-600">Only CSV, XLSX, and PDF files are accepted.</p> : null}
      <button
        type="button"
        onClick={onUpload}
        disabled={!selected || !isAllowed || loading}
        className="btn-primary mt-3 w-full disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
      {message ? <p className="mt-2 text-xs text-gray-700">{message}</p> : null}
    </section>
  );
}
