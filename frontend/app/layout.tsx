import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AI Workbench",
  description: "Chat, ingestion, reports, and system status for the grounded AI backend.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto flex min-h-screen w-full max-w-[1500px] flex-col px-4 py-4 md:px-6">
          <header className="mb-4 flex items-center justify-between rounded-2xl border border-stroke bg-panel px-4 py-3">
            <div>
              <h1 className="text-lg font-semibold">Agentic AI Workbench</h1>
              <p className="text-sm text-gray-600">Grounded answers from real Supabase data only</p>
            </div>
            <nav className="flex gap-2 text-sm">
              <Link href="/workbench" className="btn-secondary">Workbench</Link>
              <Link href="/students" className="btn-secondary">Students</Link>
              <Link href="/documents" className="btn-secondary">Documents</Link>
              <Link href="/reports" className="btn-secondary">Reports</Link>
              <Link href="/status" className="btn-secondary">Status</Link>
            </nav>
          </header>
          <main className="flex-1 animate-rise">{children}</main>
        </div>
      </body>
    </html>
  );
}
