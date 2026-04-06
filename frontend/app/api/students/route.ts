import { NextResponse } from "next/server";

import { backendHeaders, backendUrl, mapBackendError } from "@/lib/backend";

export async function GET() {
  const res = await fetch(backendUrl("/students?limit=200&offset=0"), {
    method: "GET",
    headers: backendHeaders(),
    cache: "no-store",
  });

  if (!res.ok) {
    return mapBackendError(res);
  }

  const data = await res.json();
  return NextResponse.json(data);
}
