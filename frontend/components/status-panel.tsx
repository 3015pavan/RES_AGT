"use client";

import { useEffect, useState } from "react";

import { fetchStatus } from "@/lib/api-client";
import type { StatusPayload } from "@/lib/types";

export function StatusPanel() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const result = await fetchStatus();
        if (active) {
          setStatus(result);
          setHistory((prev) => {
            const line = `${new Date().toLocaleTimeString()} health=${result.health.status} ready=${String(result.ready.ready)} req=${result.metrics.requests_total}`;
            return [line, ...prev].slice(0, 6);
          });
        }
      } catch {
        if (active) {
          setError("Unable to fetch status");
          setHistory((prev) => [`${new Date().toLocaleTimeString()} status fetch failed`, ...prev].slice(0, 6));
        }
      }
    }

    void load();
    const timer = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <section className="card p-3">
      <h3 className="mb-2 text-sm font-semibold">System Status</h3>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      {!status ? <p className="text-xs text-gray-600">Loading...</p> : null}
      {status ? (
        <div className="space-y-1 text-xs text-gray-700">
          <p>Health: {status.health.status}</p>
          <p>Ready: {String(status.ready.ready)}</p>
          <p>Reason: {status.ready.reason}</p>
          <p>Requests: {status.metrics.requests_total}</p>
          <p>Errors: {status.metrics.errors_total}</p>
          <p>Avg latency: {status.metrics.avg_latency_seconds}s</p>

          <div className="mt-2 rounded-lg border border-stroke bg-white p-2">
            <p className="mb-1 font-medium">Recent status logs</p>
            {history.length === 0 ? <p>No logs yet.</p> : null}
            {history.map((line) => (
              <p key={line} className="font-mono text-[11px]">{line}</p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
