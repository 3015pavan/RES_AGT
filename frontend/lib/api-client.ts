import axios from "axios";
import type {
  DocumentRow,
  PollResult,
  ReportPayload,
  StatusPayload,
  StudentRow,
  UploadResult,
} from "@/lib/types";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

export async function sendChat(message: string): Promise<{ response: string; intent?: string }> {
  const { data } = await client.post("/chat", { query: message });
  return {
    response: data?.response ?? data?.answer ?? "NO DATA AVAILABLE",
    intent: data?.intent,
  };
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function pollEmail(): Promise<PollResult> {
  const { data } = await client.post("/email/poll");
  return data;
}

export async function fetchStudents(): Promise<StudentRow[]> {
  const { data } = await client.get("/students");
  return data.data ?? [];
}

export async function fetchDocuments(): Promise<DocumentRow[]> {
  const { data } = await client.get("/documents");
  return data.data ?? [];
}

export async function generateReport(payload: ReportPayload): Promise<unknown> {
  const { data } = await client.post("/report", payload);
  return data;
}

export async function fetchStatus(): Promise<StatusPayload> {
  const { data } = await client.get("/status");
  return data;
}
