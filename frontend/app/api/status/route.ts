import { NextResponse } from "next/server";

import { backendHeaders, backendUrl } from "@/lib/backend";

async function safeFetch(path: string): Promise<unknown> {
  try {
    const res = await fetch(backendUrl(path), {
      method: "GET",
      headers: backendHeaders(),
      cache: "no-store",
    });
    if (!res.ok) {
      return { error: `HTTP ${res.status}` };
    }
    return res.json();
  } catch {
    return { error: "unreachable" };
  }
}

export async function GET() {
  const [health, ready, metrics] = await Promise.all([
    safeFetch("/health"),
    safeFetch("/ready"),
    safeFetch("/metrics"),
  ]);

  return NextResponse.json({ health, ready, metrics });
}
