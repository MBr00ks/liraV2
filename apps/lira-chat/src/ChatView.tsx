import { useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  mode?: string;
  streaming?: boolean;
  image_url?: string;
}

function formatContent(text: string) {
  const parts = text.split(/(\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("*") && part.endsWith("*")) {
      return (
        <span key={i} className="text-amber-300 italic font-semibold">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function ChatView({
  messages,
  onInterrupt,
}: {
  messages: Message[];
  onInterrupt: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isStreaming = messages.some((m) => m.streaming);

  return (
    <div className="flex-1 overflow-y-auto space-y-4 px-4 py-6">
      {messages.map((m, i) => (
        <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
          <div
            className={`max-w-[75%] rounded-2xl px-4 py-2 ${
              m.role === "user"
                ? "bg-cyan-700 text-white rounded-br-md"
                : "bg-zinc-800 text-zinc-100 rounded-bl-md"
            }`}
          >
            {m.mode && (
              <span className="text-xs text-zinc-500 block mb-1">{m.mode}</span>
            )}
            {m.image_url && (
              <img src={m.image_url} alt="generated" className="max-w-full rounded-lg mb-2" />
            )}
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {formatContent(m.content)}
              {m.streaming && <span className="animate-pulse">▊</span>}
            </div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
      {isStreaming && (
        <div className="flex justify-center">
          <button
            onClick={onInterrupt}
            className="text-xs text-zinc-500 hover:text-zinc-300 underline"
          >
            Interrupt
          </button>
        </div>
      )}
    </div>
  );
}
