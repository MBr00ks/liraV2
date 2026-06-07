import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from "react";
import { createWs, type WSMessage } from "./useWebSocket";
import type { LoreEntry } from "./LorePanel";
import type { ToastMsg } from "./ErrorToast";
import { AudioPlayer } from "./audio-player";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  mode?: string;
  streaming?: boolean;
  image_url?: string;
}

interface WsContextValue {
  send: (data: any) => void;
  connected: boolean;
  messages: ChatMessage[];
  mode: string;
  loreEntries: LoreEntry[];
  systemPreview: string;
  injectedLore: any[];
  editingEntry: LoreEntry | null;
  setEditingEntry: (entry: LoreEntry | null) => void;
  debugVisible: boolean;
  setDebugVisible: (v: boolean) => void;
  ttsEnabled: boolean;
  reactionsEnabled: boolean;
  pauseMultiplier: number;
  setTtsEnabled: (v: boolean) => void;
  setReactionsEnabled: (v: boolean) => void;
  setPauseMultiplier: (v: number) => void;
  handleSend: (text: string) => void;
  handleClear: () => void;
  handleInterrupt: () => void;
  handleToggleWorldbook: (worldbook: string, mode: string, active: boolean) => void;
  handleRefreshLore: () => void;
  handleEdit: (entry: LoreEntry) => void;
  handleSaveLore: (entry: LoreEntry) => void;
  handleDeleteLore: (entry: LoreEntry) => void;
  handleDeleteWorldbook: (worldbook: string) => void;
  handleExportWorldbook: (worldbook: string) => void;
  handleMoveEntry: (entryId: string, direction: "up" | "down") => void;
  handleMoveWorldbook: (worldbook: string, direction: "up" | "down") => void;
  handleQuickUpdate: (entryId: string, fields: Partial<LoreEntry>) => void;
  handleLorePageCreate: () => void;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  setMode: (m: string) => void;
  toasts: ToastMsg[];
  removeToast: (id: number) => void;
  showPersonalityEditor: boolean;
  setShowPersonalityEditor: (v: boolean) => void;
}

const Ctx = createContext<WsContextValue | null>(null);

export function useWs() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useWs must be inside WebSocketProvider");
  return c;
}

export default function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, _setMode] = useState("assistant");
  const [loreEntries, setLoreEntries] = useState<LoreEntry[]>([]);
  const [debugVisible, setDebugVisible] = useState(false);
  const [systemPreview, setSystemPreview] = useState("");
  const [injectedLore, setInjectedLore] = useState<any[]>([]);
  const [editingEntry, setEditingEntry] = useState<LoreEntry | null>(null);
  const [ttsEnabled, setTtsEnabled] = useState(() => {
    try { return localStorage.getItem("lira_tts") !== "false"; } catch { return true; }
  });
  const [reactionsEnabled, setReactionsEnabled] = useState(() => {
    try { return localStorage.getItem("lira_reactions") !== "false"; } catch { return true; }
  });
  const [pauseMultiplier, setPauseMultiplier] = useState(() => {
    try { const v = localStorage.getItem("lira_pause"); return v ? parseFloat(v) : 1.0; } catch { return 1.0; }
  });
  const [showPersonalityEditor, setShowPersonalityEditor] = useState(false);

  useEffect(() => { try { localStorage.setItem("lira_tts", String(ttsEnabled)); } catch { /* ignore */ } }, [ttsEnabled]);
  useEffect(() => { try { localStorage.setItem("lira_reactions", String(reactionsEnabled)); } catch { /* ignore */ } }, [reactionsEnabled]);
  useEffect(() => { try { localStorage.setItem("lira_pause", String(pauseMultiplier)); } catch { /* ignore */ } }, [pauseMultiplier]);

  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const toastId = useRef(0);
  const pushToast = useCallback((text: string, type: ToastMsg["type"] = "info") => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, text, type }]);
  }, []);
  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef(new AudioPlayer());
  const interruptRef = useRef(false);
  const imgGenId = useRef(0);
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const send = useCallback((data: any) => {
    try {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(data));
      }
    } catch { /* ignore */ }
  }, []);

  const onMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "text":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.streaming) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...last,
              content: last.content + msg.delta,
            };
            return updated;
          }
          return [
            ...prev,
            { role: "assistant", content: msg.delta, mode: modeRef.current, streaming: true },
          ];
        });
        break;
      case "audio":
        if (!interruptRef.current) audioRef.current.enqueue(msg.chunk, (msg as any).seq);
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
        pushToast(msg.message, "error");
        break;
      case "lore_injected":
        setSystemPreview(msg.system_preview);
        setInjectedLore(msg.lore);
        break;
      case "lore_list":
        setLoreEntries(msg.entries);
        break;
      case "worldbook_toggled":
        setLoreEntries((prev) =>
          prev.map((e) => {
            if (e.source_worldbook !== msg.worldbook) return e;
            const modes = e.modes || [];
            if (msg.active && !modes.includes(msg.mode))
              return { ...e, modes: [...modes, msg.mode] };
            if (!msg.active && modes.includes(msg.mode))
              return { ...e, modes: modes.filter((m: string) => m !== msg.mode) };
            return e;
          })
        );
        break;
      case "lore_toggled":
        setLoreEntries((prev) => prev.map((e) => (e.id === msg.entry?.id ? msg.entry : e)));
        break;
      case "lore_updated":
        setLoreEntries((prev) => prev.map((e) => (e.id === msg.entry?.id ? msg.entry : e)));
        setEditingEntry(null);
        break;
      case "mode_set":
        _setMode(msg.mode);
        break;
      case "tts_error":
        pushToast(msg.message, "error");
        break;
    }
  }, []);

  const disconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const connect = useCallback(() => {
    // Skip if we already have a healthy connection
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;
    wsRef.current?.close();
    const ws = createWs(onMessage,
      () => {
        if (wsRef.current !== ws) return;
        setConnected(true);
        clearTimeout(disconnectTimer.current);
        send({ type: "get_lore" });
      },
      () => {
        if (wsRef.current !== ws) return;
        setConnected(false);
        clearTimeout(disconnectTimer.current);
        disconnectTimer.current = setTimeout(() => {
          pushToast("Connection lost — reconnecting...", "error");
        }, 2000);
      }
    );
    wsRef.current = ws;
  }, [onMessage, send, pushToast]);

  useEffect(() => { connect(); }, [connect]);

  const handleSend = useCallback((text: string) => {
    const imagineMatch = text.match(/^\/imagine\s+(.+)/);
    if (imagineMatch) {
      const prompt = imagineMatch[1];
      const genId = ++imgGenId.current;
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: `Generating... (#${genId})`, streaming: true },
      ]);
      fetch("/api/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      })
        .then(async (resp) => {
          if (!resp.ok) { const err = await resp.json(); throw new Error(err.error || resp.statusText); }
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          setMessages((prev) => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].content === `Generating... (#${genId})`) {
                updated[i] = { role: "assistant", content: prompt, streaming: false, image_url: url };
                break;
              }
            }
            return updated;
          });
        })
        .catch((err) => {
          pushToast(`Image generation failed: ${err.message}`, "error");
          setMessages((prev) => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].content === `Generating... (#${genId})`) {
                updated[i] = { role: "assistant", content: `Error: ${err.message}`, streaming: false };
                break;
              }
            }
            return updated;
          });
        });
      return;
    }
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    send({ type: "message", text });
  }, [send, pushToast]);

  const setMode = useCallback((m: string) => {
    _setMode(m);
    send({ type: "set_mode", mode: m });
  }, [send]);

  const handleClear = useCallback(() => {
    setMessages([]);
    send({ type: "clear_history" });
  }, [send]);

  const handleInterrupt = useCallback(() => {
    interruptRef.current = true;
    audioRef.current.interrupt();
    wsRef.current?.close();
    connect();
    setTimeout(() => { interruptRef.current = false; }, 100);
  }, [connect]);

  const handleEdit = useCallback((entry: LoreEntry) => {
    setEditingEntry(entry);
  }, []);

  const handleToggleWorldbook = useCallback(
    (worldbook: string, m: string, active: boolean) => {
      send({ type: "toggle_worldbook", worldbook, mode: m, active });
    }, [send]);
  const handleRefreshLore = useCallback(() => { send({ type: "get_lore" }); }, [send]);
  const handleSaveLore = useCallback((entry: LoreEntry) => { send({ type: "update_lore", entry }); }, [send]);
  const handleDeleteLore = useCallback((entry: LoreEntry) => {
    fetch(`/api/lore/entry/${entry.id}`, { method: "DELETE" })
      .then(() => {
        send({ type: "get_lore" });
        setEditingEntry(null);
      })
      .catch((err) => pushToast(`Failed to delete lore: ${err.message}`, "error"));
  }, [send, pushToast]);
  const handleDeleteWorldbook = useCallback((worldbook: string) => {
    fetch(`/api/lore/worldbook/${encodeURIComponent(worldbook)}`, { method: "DELETE" })
      .then(() => { send({ type: "get_lore" }); })
      .catch((err) => pushToast(`Failed to delete worldbook: ${err.message}`, "error"));
  }, [send, pushToast]);

  const handleExportWorldbook = useCallback(async (worldbook: string) => {
    try {
      const resp = await fetch(`/api/lore/export?worldbook=${encodeURIComponent(worldbook)}`);
      const data = await resp.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${worldbook.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      pushToast(`Export failed: ${err.message}`, "error");
    }
  }, [pushToast]);

  const handleMoveEntry = useCallback((entryId: string, direction: "up" | "down") => {
    fetch(`/api/lore/entry/${entryId}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    }).then(() => send({ type: "get_lore" }))
      .catch((err) => pushToast(`Move failed: ${err.message}`, "error"));
  }, [send, pushToast]);

  const handleMoveWorldbook = useCallback((worldbook: string, direction: "up" | "down") => {
    fetch(`/api/lore/worldbook/${encodeURIComponent(worldbook)}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    }).then(() => send({ type: "get_lore" }))
      .catch((err) => pushToast(`Move failed: ${err.message}`, "error"));
  }, [send, pushToast]);

  const handleQuickUpdate = useCallback((entryId: string, fields: Partial<LoreEntry>) => {
    fetch(`/api/lore/entry/${entryId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    }).then(() => send({ type: "get_lore" }))
      .catch((err) => pushToast(`Update failed: ${err.message}`, "error"));
  }, [send, pushToast]);

  const handleLorePageCreate = useCallback(() => { send({ type: "get_lore" }); }, [send]);

  return (
    <Ctx.Provider value={{
      send, connected, messages, mode, loreEntries, systemPreview, injectedLore,
      editingEntry, setEditingEntry, debugVisible, setDebugVisible,
      ttsEnabled, reactionsEnabled, pauseMultiplier,
      setTtsEnabled, setReactionsEnabled, setPauseMultiplier,
      handleSend, handleClear, handleInterrupt,
      handleEdit, handleToggleWorldbook, handleRefreshLore, handleSaveLore, handleDeleteLore,
      handleDeleteWorldbook, handleExportWorldbook,
      handleMoveEntry, handleMoveWorldbook, handleQuickUpdate,
      handleLorePageCreate, setMessages, setMode, toasts, removeToast,
      showPersonalityEditor, setShowPersonalityEditor,
    }}>
      {children}
    </Ctx.Provider>
  );
}
