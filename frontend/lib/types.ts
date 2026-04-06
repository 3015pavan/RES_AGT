export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

export type UploadResult = {
  rows_ingested: number;
  documents_created: number;
  document_ids: string[];
  status: string;
};

export type PollResult = {
  processed: number;
  failed: number;
};

export type StudentRow = {
  id: string;
  usn: string;
  student_name: string | null;
  semester: number | null;
  section: string | null;
  sgpa?: number | null;
};

export type DocumentRow = {
  id: string;
  source_type: string;
  file_name: string;
  mime_type: string;
  created_at: string;
};

export type ReportPayload = {
  report_type: "student" | "class" | "subject";
  filters: Record<string, string | number>;
};

export type StatusPayload = {
  health: { status: string };
  ready: { ready: boolean; reason: string };
  metrics: {
    requests_total: number;
    errors_total: number;
    requests_by_status: Record<string, number>;
    avg_latency_seconds: number;
  };
};
