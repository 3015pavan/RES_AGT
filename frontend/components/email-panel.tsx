"use client";

import { useState } from "react";

import { pollEmail } from "@/lib/api-client";

export function EmailPanel() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function onPoll() {
    if (loading) {
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const data = await pollEmail();
      setMessage(`Processed: ${data.processed}, Failed: ${data.failed}`);
    } catch {
      setMessage("Email poll failed or disabled on backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card p-3">
      <h3 className="mb-2 text-sm font-semibold">Email Ingestion</h3>
      <button type="button" className="btn-secondary w-full" onClick={onPoll} disabled={loading}>
        {loading ? "Polling..." : "Poll Unread Emails"}
      </button>
      {message ? <p className="mt-2 text-xs text-gray-700">{message}</p> : null}
    </section>
  );
}
