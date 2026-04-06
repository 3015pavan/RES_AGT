import { ChatPanel } from "@/components/chat-panel";
import { EmailPanel } from "@/components/email-panel";
import { StatusPanel } from "@/components/status-panel";
import { UploadPanel } from "@/components/upload-panel";

export default function WorkbenchPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="space-y-4">
        <UploadPanel />
        <EmailPanel />
        <StatusPanel />
      </aside>
      <ChatPanel />
    </div>
  );
}
