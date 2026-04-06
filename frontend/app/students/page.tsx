import { StudentsTable } from "@/components/students-table";

export default function StudentsPage() {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Students</h2>
      <StudentsTable />
    </section>
  );
}
