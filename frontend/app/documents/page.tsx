import { DocumentsTable } from "@/components/documents-table";

export default function DocumentsPage() {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Documents</h2>
      <DocumentsTable />
    </section>
  );
}
