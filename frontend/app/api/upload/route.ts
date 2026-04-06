import { NextRequest, NextResponse } from "next/server";

import { backendHeaders, backendUrl, mapBackendError } from "@/lib/backend";

const allowedExt = ["csv", "xlsx", "pdf"];

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const file = form.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "File is required" }, { status: 400 });
  }

  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!allowedExt.includes(ext)) {
    return NextResponse.json({ error: "Only CSV, XLSX, and PDF are allowed" }, { status: 400 });
  }

  const forward = new FormData();
  forward.append("file", file);

  const res = await fetch(backendUrl("/upload"), {
    method: "POST",
    headers: backendHeaders(),
    body: forward,
    cache: "no-store",
  });

  if (!res.ok) {
    return mapBackendError(res);
  }

  const data = await res.json();
  return NextResponse.json(data);
}
