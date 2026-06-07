import { useState } from "react";

const ACTIVATION_OPTIONS = [
  { value: "always", label: "Core (always injected)" },
  { value: "mode", label: "Context (mode match)" },
  { value: "trigger", label: "On Trigger (keyword match)" },
];

interface LoreEntry {
  id: string;
  title: string;
  content: string;
  enabled: boolean;
  activation: string;
  modes: string[] | null;
  trigger_keywords: string[] | null;
  source_worldbook?: string;
}

export default function LoreCreator({
  onCreated,
  onClose,
  inline,
}: {
  onCreated: (entry: LoreEntry) => void;
  onClose: () => void;
  inline?: boolean;
}) {
  const [tab, setTab] = useState<"entry" | "worldbook">("entry");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [activation, setActivation] = useState("trigger");
  const [keywords, setKeywords] = useState("");
  const [worldbook, setWorldbook] = useState("Custom");
  const [wbName, setWbName] = useState("");
  const [wbModes, setWbModes] = useState("assistant");
  const [creating, setCreating] = useState(false);

  const handleCreateEntry = async () => {
    setCreating(true);
    try {
      const resp = await fetch("/api/lore/entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title || "New Entry",
          content,
          activation,
          trigger_keywords: activation === "trigger" && keywords.trim()
            ? keywords.split(",").map((k) => k.trim()).filter(Boolean)
            : [],
          source_worldbook: worldbook,
        }),
      });
      const data = await resp.json();
      onCreated(data.entry);
    } finally {
      setCreating(false);
    }
  };

  const handleCreateWorldbook = async () => {
    if (!wbName.trim()) return;
    setCreating(true);
    try {
      await fetch("/api/lore/worldbook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: wbName,
          modes: wbModes.split(",").map((m) => m.trim()).filter(Boolean),
        }),
      });
      onClose();
    } finally {
      setCreating(false);
    }
  };

  const body = (
    <>
      {/* Tabs */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => setTab("entry")}
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            tab === "entry"
              ? "bg-cyan-700 text-white"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          New Entry
        </button>
        <button
          onClick={() => setTab("worldbook")}
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            tab === "worldbook"
              ? "bg-cyan-700 text-white"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          New Worldbook
        </button>
      </div>

      {/* Body */}
      <div className="space-y-4">
        {tab === "entry" ? (
          <>
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="New Entry"
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Content</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={6}
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600 font-mono resize-y"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Activation</label>
              <select
                value={activation}
                onChange={(e) => setActivation(e.target.value)}
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              >
                {ACTIVATION_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            {activation === "trigger" && (
              <div>
                <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Trigger keywords (comma-separated)</label>
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="keyword1, keyword2, ..."
                  className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Worldbook</label>
              <input
                type="text"
                value={worldbook}
                onChange={(e) => setWorldbook(e.target.value)}
                placeholder="Custom"
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Worldbook Name</label>
              <input
                type="text"
                value={wbName}
                onChange={(e) => setWbName(e.target.value)}
                placeholder="My Worldbook"
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">Default modes (comma-separated)</label>
              <input
                type="text"
                value={wbModes}
                onChange={(e) => setWbModes(e.target.value)}
                placeholder="assistant, companion, observer"
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              />
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-zinc-700">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={tab === "entry" ? handleCreateEntry : handleCreateWorldbook}
          disabled={creating}
          className="px-4 py-2 text-sm bg-cyan-700 hover:bg-cyan-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {creating ? "Creating..." : tab === "entry" ? "Create Entry" : "Create Worldbook"}
        </button>
      </div>
    </>
  );

  if (inline) {
    return body;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-lg mx-4 flex flex-col p-5">
        {body}
      </div>
    </div>
  );
}
