import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from "react";
import type { TransportAdapter } from "../transport/TransportAdapter";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  mode?: string;
  streaming?: boolean;
  image_url?: string;
}

interface ChatContextValue {
  messages: ChatMessage[];
  connected: boolean;
  mode: string;
  handleSend: (text: string) => void;
  handleClear: () => void;
  handleInterrupt: () => void;
  handleRetry: () => void;
  handleCopy: (index: number) => void;
  handleDeleteMessage: (index: number) => void;
  setMode: (m: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

const Ctx = createContext<ChatContextValue | null>(null);

export function useChat() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useChat must be inside ChatProvider");
  return c;
}

export function ChatProvider({
  transport,
  children,
  onToast,
}: {
  transport: TransportAdapter;
  children: ReactNode;
  onToast?: (text: string, type?: "error" | "info" | "success") => void;
}) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, _setMode] = useState("assistant");
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const messagesRef = useRef<ChatMessage[]>([]);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  const connect = useCallback(() => {
    transport.connect().then(() => {
      setConnected(true);
      transport.send({ type: "get_lore" });
    });
  }, [transport]);

  useEffect(() => { connect(); }, [connect]);

  transport.onMessage(useCallback((msg: any) => {
    switch (msg.type) {
      case "text":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.streaming) {
            const updated = [...prev];
            updated[updated.length - 1] = { ...last, content: last.content + msg.delta };
            return updated;
          }
          return [...prev, { role: "assistant", content: msg.delta, mode: modeRef.current, streaming: true }];
        });
        break;
      case "done":
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.streaming) updated[updated.length - 1] = { ...last, streaming: false };
          return updated;
        });
        break;
      case "error":
        onToast?.(msg.message, "error");
        break;
      case "mode_set":
        _setMode(msg.mode);
        break;
      case "image": {
        const blob = new Blob(
          [Uint8Array.from(atob(msg.data), (c) => c.charCodeAt(0))],
          { type: "image/png" },
        );
        const url = URL.createObjectURL(blob);
        setMessages((prev) => [...prev, { role: "assistant", content: msg.prompt, image_url: url }]);
        break;
      }
      case "tts_error":
        onToast?.(msg.message, "error");
        break;
    }
  }, [onToast]));

  const handleSend = useCallback((text: string) => {
    const imagineMatch = text.match(/^\/imagine\s+(.+)/);
    if (imagineMatch) {
      const prompt = imagineMatch[1];
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      fetch("/api/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      })
        .then(async (resp) => {
          if (!resp.ok) { const err = await resp.json(); throw new Error(err.error || resp.statusText); }
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          setMessages((prev) => [...prev, { role: "assistant", content: prompt, image_url: url }]);
        })
        .catch((err) => onToast?.(`Image gen failed: ${err.message}`, "error"));
      return;
    }
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    transport.send({ type: "message", text });
  }, [transport, onToast]);

  const handleClear = useCallback(() => {
    setMessages([]);
    transport.send({ type: "clear_history" });
  }, [transport]);

  const handleInterrupt = useCallback(() => {
    transport.disconnect();
    connect();
  }, [transport, connect]);

  const setMode = useCallback((m: string) => {
    _setMode(m);
    transport.send({ type: "set_mode", mode: m });
  }, [transport]);

  const handleCopy = useCallback((index: number) => {
    const msg = messagesRef.current[index];
    if (msg) {
      navigator.clipboard.writeText(msg.content).catch(() => {});
      onToast?.("Copied", "info");
    }
  }, [onToast]);

  const handleDeleteMessage = useCallback((index: number) => {
    setMessages((prev) => {
      const updated = [...prev];
      if (updated[index]?.image_url) URL.revokeObjectURL(updated[index].image_url!);
      updated.splice(index, 1);
      return updated;
    });
    transport.send({ type: "delete_message", index });
  }, [transport]);

  const handleRetry = useCallback(() => {
    const msgs = messagesRef.current;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "user") {
        setMessages((prev) => {
          const updated = [...prev];
          if (updated[updated.length - 1]?.role === "assistant") updated.pop();
          return updated;
        });
        handleSend(msgs[i].content);
        return;
      }
    }
  }, [handleSend]);

  return (
    <Ctx.Provider value={{
      messages, connected, mode, handleSend, handleClear, handleInterrupt,
      handleRetry, handleCopy, handleDeleteMessage, setMode, setMessages,
    }}>
      {children}
    </Ctx.Provider>
  );
}
