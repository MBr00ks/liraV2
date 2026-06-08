/** Legacy compatibility wrapper — exposes useWs() interface backed by new providers. */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { TransportAdapter } from "./transport/TransportAdapter";
import type { LoreEntry } from "./LorePanel";
import type { ToastMsg } from "./ErrorToast";
import { useChat } from "./providers/ChatProvider";
import { useAudio } from "./providers/AudioProvider";
import { useToasts } from "./providers/ToastProvider";

interface WsLegacyValue {
  send: (data: any) => void;
  connected: boolean;
  messages: any[];
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
  setMessages: React.Dispatch<React.SetStateAction<any[]>>;
  setMode: (m: string) => void;
  toasts: ToastMsg[];
  removeToast: (id: number) => void;
  showPersonalityEditor: boolean;
  setShowPersonalityEditor: (v: boolean) => void;
  handleCopy: (index: number) => void;
  handleDeleteMessage: (index: number) => void;
  handleRetry: () => void;
}

const Ctx = createContext<WsLegacyValue | null>(null);

export function useWs() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useWs must be inside WebSocketProvider");
  return c;
}

export default function WebSocketProvider({
  children,
  transport,
}: {
  children: ReactNode;
  transport: TransportAdapter;
}) {
  const chat = useChat();
  const audio = useAudio();
  const { toasts, pushToast, removeToast } = useToasts();
  const [loreEntries, setLoreEntries] = useState<LoreEntry[]>([]);
  const [systemPreview, setSystemPreview] = useState("");
  const [injectedLore, setInjectedLore] = useState<any[]>([]);
  const [editingEntry, setEditingEntry] = useState<LoreEntry | null>(null);
  const [showPersonalityEditor, setShowPersonalityEditor] = useState(false);

  // Listen for lore-related messages from transport
  useEffect(() => {
    const unsub = transport.onMessage((msg: any) => {
      switch (msg.type) {
        case "lore_list":
          setLoreEntries(msg.entries);
          break;
        case "lore_injected":
          setSystemPreview(msg.system_preview);
          setInjectedLore(msg.lore);
          break;
        case "lore_toggled":
          setLoreEntries((prev) => prev.map((e) => (e.id === msg.entry?.id ? msg.entry : e)));
          break;
        case "lore_updated":
          setLoreEntries((prev) => prev.map((e) => (e.id === msg.entry?.id ? msg.entry : e)));
          setEditingEntry(null);
          break;
        case "worldbook_toggled":
          setLoreEntries((prev) =>
            prev.map((e) => {
              if (e.source_worldbook !== msg.worldbook) return e;
              const modes = e.modes || [];
              if (msg.active && !modes.includes(msg.mode)) return { ...e, modes: [...modes, msg.mode] };
              if (!msg.active && modes.includes(msg.mode)) return { ...e, modes: modes.filter((m: string) => m !== msg.mode) };
              return e;
            }),
          );
          break;
      }
    });
    return unsub;
  }, [transport]);

  // Lore handlers
  const handleToggleWorldbook = useCallback((wb: string, m: string, active: boolean) => {
    transport.send({ type: "toggle_worldbook", worldbook: wb, mode: m, active });
  }, [transport]);

  const handleRefreshLore = useCallback(() => {
    transport.send({ type: "get_lore" });
  }, [transport]);

  const handleEdit = useCallback((entry: LoreEntry) => setEditingEntry(entry), []);

  const handleSaveLore = useCallback((entry: LoreEntry) => {
    transport.send({ type: "update_lore", entry });
  }, [transport]);

  const handleDeleteLore = useCallback((entry: LoreEntry) => {
    fetch(`/api/lore/entry/${entry.id}`, { method: "DELETE" })
      .then(() => { transport.send({ type: "get_lore" }); setEditingEntry(null); })
      .catch((err) => pushToast(`Delete failed: ${err.message}`, "error"));
  }, [transport, pushToast]);

  const handleDeleteWorldbook = useCallback((wb: string) => {
    fetch(`/api/lore/worldbook/${encodeURIComponent(wb)}`, { method: "DELETE" })
      .then(() => transport.send({ type: "get_lore" }))
      .catch((err) => pushToast(`Delete failed: ${err.message}`, "error"));
  }, [transport, pushToast]);

  const handleExportWorldbook = useCallback(async (wb: string) => {
    try {
      const resp = await fetch(`/api/lore/export?worldbook=${encodeURIComponent(wb)}`);
      const data = await resp.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${wb.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`; a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      pushToast(`Export failed: ${err.message}`, "error");
    }
  }, [pushToast]);

  const handleMoveEntry = useCallback((entryId: string, direction: "up" | "down") => {
    fetch(`/api/lore/entry/${entryId}/move`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    }).then(() => transport.send({ type: "get_lore" }))
      .catch((err) => pushToast(`Move failed: ${err.message}`, "error"));
  }, [transport, pushToast]);

  const handleMoveWorldbook = useCallback((wb: string, direction: "up" | "down") => {
    fetch(`/api/lore/worldbook/${encodeURIComponent(wb)}/move`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    }).then(() => transport.send({ type: "get_lore" }))
      .catch((err) => pushToast(`Move failed: ${err.message}`, "error"));
  }, [transport, pushToast]);

  const handleQuickUpdate = useCallback((entryId: string, fields: Partial<LoreEntry>) => {
    fetch(`/api/lore/entry/${entryId}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    }).then(() => transport.send({ type: "get_lore" }))
      .catch((err) => pushToast(`Update failed: ${err.message}`, "error"));
  }, [transport, pushToast]);

  const handleLorePageCreate = useCallback(() => transport.send({ type: "get_lore" }), [transport]);

  return (
    <Ctx.Provider value={{
      send: (data: any) => {
        const { type, ...rest } = data;
        transport.send({ type, ...rest } as any);
      },
      connected: chat.connected,
      messages: chat.messages,
      mode: chat.mode,
      loreEntries,
      systemPreview,
      injectedLore,
      editingEntry, setEditingEntry,
      debugVisible: audio.debugVisible,
      setDebugVisible: audio.setDebugVisible,
      ttsEnabled: audio.ttsEnabled,
      reactionsEnabled: audio.reactionsEnabled,
      pauseMultiplier: audio.pauseMultiplier,
      setTtsEnabled: audio.setTtsEnabled,
      setReactionsEnabled: audio.setReactionsEnabled,
      setPauseMultiplier: audio.setPauseMultiplier,
      handleSend: chat.handleSend,
      handleClear: chat.handleClear,
      handleInterrupt: chat.handleInterrupt,
      handleToggleWorldbook, handleRefreshLore, handleEdit,
      handleSaveLore, handleDeleteLore, handleDeleteWorldbook,
      handleExportWorldbook, handleMoveEntry, handleMoveWorldbook,
      handleQuickUpdate, handleLorePageCreate,
      setMessages: chat.setMessages,
      setMode: chat.setMode,
      toasts, removeToast,
      showPersonalityEditor, setShowPersonalityEditor,
      handleCopy: chat.handleCopy,
      handleDeleteMessage: chat.handleDeleteMessage,
      handleRetry: chat.handleRetry,
    }}>
      {children}
    </Ctx.Provider>
  );
}
