import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useWs } from "./WebSocketProvider";
import ModeSelector from "./ModeSelector";
import PersonalityEditor from "./PersonalityEditor";
import LoreEditModal from "./LoreEditModal";
import ErrorToast from "./ErrorToast";

export default function App() {
  const {
    connected, mode, setMode,
    showPersonalityEditor, setShowPersonalityEditor,
    editingEntry, setEditingEntry,
    handleSaveLore, handleDeleteLore,
    handleClear, toasts, removeToast,
  } = useWs();
  const navigate = useNavigate();
  const location = useLocation();
  const isLore = location.pathname === "/lore";

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100">
      <header className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-cyan-400">Lira</h1>
          <span className={`text-xs px-2 py-0.5 rounded-full ${connected ? "bg-green-800 text-green-300" : "bg-zinc-800 text-zinc-500"}`}>
            {connected ? "connected" : "disconnected"}
          </span>
          <button
            onClick={handleClear}
            disabled={!connected}
            className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-30 px-2 py-0.5 rounded border border-zinc-700 hover:border-zinc-500 transition-colors"
          >
            Clear
          </button>
          <button
            onClick={() => navigate(isLore ? "/" : "/lore")}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              isLore
                ? "bg-cyan-800 text-cyan-200 border-cyan-700"
                : "text-zinc-500 hover:text-zinc-300 border-zinc-700 hover:border-zinc-500"
            }`}
          >
            Lore
          </button>
          <button
            onClick={() => setShowPersonalityEditor(true)}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-0.5 rounded border border-zinc-700 hover:border-zinc-500 transition-colors"
          >
            Personality
          </button>
        </div>
        <ModeSelector active={mode} onChange={setMode} />
      </header>
      <div className="flex-1 overflow-hidden relative">
        <Outlet />
      </div>
      {showPersonalityEditor && (
        <PersonalityEditor onClose={() => setShowPersonalityEditor(false)} />
      )}
      {editingEntry && (
        <LoreEditModal
          entry={editingEntry}
          onSave={handleSaveLore}
          onDelete={handleDeleteLore}
          onClose={() => setEditingEntry(null)}
        />
      )}
      <ErrorToast toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
