import { NextResponse } from "next/server";

const backendBaseUrl = process.env.BACKEND_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const backendApiKey = process.env.BACKEND_API_KEY ?? process.env.API_KEY ?? "";

export function backendUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export function backendHeaders(extra: HeadersInit = {}): HeadersInit {
  return {
    "x-api-key": backendApiKey,
    ...extra,
  };
}

export async function mapBackendError(res: Response) {
  let message = "Server error";
  try {
    const payload = await res.json();
    message = payload?.error?.message ?? payload?.detail ?? message;
  } catch {
    // Ignore parse errors and keep default message.
  }
  return NextResponse.json({ error: message }, { status: res.status || 500 });
}
