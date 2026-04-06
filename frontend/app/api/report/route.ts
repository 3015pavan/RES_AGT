import { NextRequest, NextResponse } from "next/server";

import { backendHeaders, backendUrl, mapBackendError } from "@/lib/backend";

export async function POST(req: NextRequest) {
  const payload = await req.json();

  const res = await fetch(backendUrl("/report"), {
    method: "POST",
    headers: backendHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!res.ok) {
    return mapBackendError(res);
  }

  const data = await res.json();
  return NextResponse.json(data);
}
