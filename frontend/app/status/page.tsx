import { StatusPanel } from "@/components/status-panel";

export default function StatusPage() {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">System Status</h2>
      <div className="max-w-[500px]">
        <StatusPanel />
      </div>
    </section>
  );
}
