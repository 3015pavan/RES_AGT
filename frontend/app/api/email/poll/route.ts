import { NextResponse } from "next/server";

import { backendHeaders, backendUrl, mapBackendError } from "@/lib/backend";

export async function POST() {
  const res = await fetch(backendUrl("/email/poll"), {
    method: "POST",
    headers: backendHeaders(),
    cache: "no-store",
  });

  if (!res.ok) {
    return mapBackendError(res);
  }

  const data = await res.json();
  return NextResponse.json(data);
}
