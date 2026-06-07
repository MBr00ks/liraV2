import { useState } from "react";

interface LoreEntry {
  id: string;
  title: string;
  content: string;
  enabled: boolean;
  activation: string;
  modes: string[] | null;
  trigger_keywords: string[] | null;
  source_worldbook?: string;
  priority?: number;
}

export default function LoreEditModal({
  entry,
  onSave,
  onDelete,
  onClose,
}: {
  entry: LoreEntry;
  onSave: (entry: LoreEntry) => void;
  onDelete?: (entry: LoreEntry) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(entry.title);
  const [content, setContent] = useState(entry.content);
  const [enabled, setEnabled] = useState(entry.enabled);
  const [activation, setActivation] = useState(entry.activation);
  const [keywords, setKeywords] = useState(
    (entry.trigger_keywords || []).join(", ")
  );

  const handleSave = () => {
    onSave({
      ...entry,
      title,
      content,
      enabled,
      activation,
      trigger_keywords:
        activation === "trigger" && keywords.trim()
          ? keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold text-zinc-100">Edit Lore Entry</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Source */}
          {entry.source_worldbook && (
            <div className="text-xs text-zinc-600">
              Worldbook: <span className="text-zinc-500">{entry.source_worldbook}</span>
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
            />
          </div>

          {/* Content */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600 font-mono resize-y"
            />
          </div>

          {/* Enabled */}
          <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="accent-cyan-600"
            />
            Enabled
          </label>

          {/* Activation */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">
              Activation
            </label>
            <select
              value={activation}
              onChange={(e) => setActivation(e.target.value)}
              className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
            >
              <option value="always">Core (always injected)</option>
              <option value="mode">Context (mode match)</option>
              <option value="trigger">On Trigger (keyword match)</option>
            </select>
          </div>

          {/* Trigger keywords (shown for trigger activation) */}
          {activation === "trigger" && (
            <div>
              <label className="block text-xs text-zinc-400 mb-1 uppercase tracking-wide">
                Trigger keywords (comma-separated)
              </label>
              <input
                type="text"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="keyword1, keyword2, ..."
                className="w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              />
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex justify-between gap-3 px-5 py-4 border-t border-zinc-700">
          <div>
            {onDelete && (
              <button
                onClick={() => onDelete(entry)}
                className="px-4 py-2 text-sm text-red-500 hover:text-red-400 rounded-lg transition-colors"
              >
                Delete
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm bg-cyan-700 hover:bg-cyan-600 text-white rounded-lg font-medium transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
