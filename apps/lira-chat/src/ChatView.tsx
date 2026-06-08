import { useRef, useEffect, useState } from "react";

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

function MessageActions({
  visible,
  onCopy,
  onDelete,
  onRetry,
  isAssistant,
}: {
  visible: boolean;
  onCopy: () => void;
  onDelete: () => void;
  onRetry?: () => void;
  isAssistant: boolean;
}) {
  if (!visible) return null;
  return (
    <div className={`absolute top-1 flex gap-0.5 ${isAssistant ? "right-1" : "left-1"}`}>
      <button
        onClick={(e) => { e.stopPropagation(); onCopy(); }}
        className="w-5 h-5 flex items-center justify-center rounded bg-black/30 hover:bg-black/50 text-zinc-400 hover:text-zinc-200 text-[10px] transition-colors"
        title="Copy"
      >
        {"\u2398"}
      </button>
      {onRetry && (
        <button
          onClick={(e) => { e.stopPropagation(); onRetry(); }}
          className="w-5 h-5 flex items-center justify-center rounded bg-black/30 hover:bg-black/50 text-zinc-400 hover:text-cyan-400 text-[10px] transition-colors"
          title="Retry"
        >
          {"\u21BB"}
        </button>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="w-5 h-5 flex items-center justify-center rounded bg-black/30 hover:bg-red-900/60 text-zinc-400 hover:text-red-400 text-[10px] transition-colors"
        title="Delete"
      >
        {"\u2715"}
      </button>
    </div>
  );
}

export default function ChatView({
  messages,
  onInterrupt,
  onCopy,
  onDelete,
  onRetry,
}: {
  messages: Message[];
  onInterrupt: () => void;
  onCopy: (index: number) => void;
  onDelete: (index: number) => void;
  onRetry: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isStreaming = messages.some((m) => m.streaming);

  return (
    <div className="flex-1 overflow-y-auto space-y-4 px-4 py-6">
      {messages.map((m, i) => (
        <div
          key={i}
          className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          onMouseEnter={() => setHoveredIdx(i)}
          onMouseLeave={() => setHoveredIdx(null)}
        >
          <div
            className={`relative max-w-[75%] rounded-2xl px-4 py-2 ${
              m.role === "user"
                ? "bg-cyan-700 text-white rounded-br-md"
                : "bg-zinc-800 text-zinc-100 rounded-bl-md"
            }`}
          >
            <MessageActions
              visible={hoveredIdx === i}
              onCopy={() => onCopy(i)}
              onDelete={() => onDelete(i)}
              onRetry={m.role === "assistant" ? onRetry : undefined}
              isAssistant={m.role === "assistant"}
            />
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
