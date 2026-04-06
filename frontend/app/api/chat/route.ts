import { NextRequest, NextResponse } from "next/server";

import { backendHeaders, backendUrl, mapBackendError } from "@/lib/backend";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const payload = {
    query: body?.query ?? body?.message ?? "",
  };

  const res = await fetch(backendUrl("/chat"), {
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
