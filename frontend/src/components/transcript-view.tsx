import { ChatInterface } from "@/components/chat-interface";
import type { TranscriptTurn } from "@/lib/types";

export function TranscriptView({ transcript }: { transcript: TranscriptTurn[] }) {
  return (
    <div className="border rounded-lg">
      <ChatInterface transcript={transcript} />
    </div>
  );
}
