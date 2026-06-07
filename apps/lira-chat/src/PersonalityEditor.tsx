import { useState, useEffect } from "react";

interface PersonalityProfile {
  mode: string;
  label: string;
  description?: string;
  system_prompt: string;
  style_guide: string;
}

export default function PersonalityEditor({
  onClose,
}: {
  onClose: () => void;
}) {
  const [profiles, setProfiles] = useState<PersonalityProfile[]>([]);
  const [selected, setSelected] = useState<string>("assistant");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [styleGuide, setStyleGuide] = useState("");
  const [saving, setSaving] = useState(false);
  const [snapshotName, setSnapshotName] = useState("");

  useEffect(() => {
    fetch("/api/personalities")
      .then((r) => r.json())
      .then((data) => {
        setProfiles(data.personalities);
        const first = data.personalities.find((p: PersonalityProfile) => p.mode === selected);
        if (first) {
          setSystemPrompt(first.system_prompt);
          setStyleGuide(first.style_guide);
        }
      });
  }, [selected]);

  const switchMode = (mode: string) => {
    const profile = profiles.find((p) => p.mode === mode);
    if (profile) {
      setSelected(mode);
      setSystemPrompt(profile.system_prompt);
      setStyleGuide(profile.style_guide);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/personalities/${selected}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_prompt: systemPrompt, style_guide: styleGuide }),
      });
      setProfiles((prev) =>
        prev.map((p) =>
          p.mode === selected
            ? { ...p, system_prompt: systemPrompt, style_guide: styleGuide }
            : p
        )
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSnapshot = async () => {
    if (!snapshotName.trim()) return;
    await fetch("/api/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: snapshotName }),
    });
    setSnapshotName("");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-[90vw] h-[85vh] mx-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-700 shrink-0">
          <h2 className="text-lg font-semibold text-zinc-100">Personality Editor</h2>
          <div className="flex items-center gap-2">
            {profiles.map((p) => (
              <button
                key={p.mode}
                onClick={() => switchMode(p.mode)}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  selected === p.mode
                    ? "bg-cyan-700 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {p.label}
              </button>
            ))}
            <span className="w-px h-5 bg-zinc-700 mx-1" />
            <button
              onClick={onClose}
              className="text-zinc-500 hover:text-zinc-300 text-xl leading-none ml-2"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Body - two column */}
        <div className="flex-1 flex min-h-0">
          {/* Left: System Prompt */}
          <div className="flex-1 flex flex-col p-4 border-r border-zinc-800">
            <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 font-semibold">
              System Prompt
            </label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="flex-1 w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600 font-mono resize-none"
            />
          </div>

          {/* Right: Style Guide */}
          <div className="flex-1 flex flex-col p-4">
            <label className="text-xs text-zinc-400 uppercase tracking-wide mb-2 font-semibold">
              Style Guide
            </label>
            <textarea
              value={styleGuide}
              onChange={(e) => setStyleGuide(e.target.value)}
              className="flex-1 w-full bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 border border-zinc-700 focus:outline-none focus:border-cyan-600 font-mono resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-700 shrink-0">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={snapshotName}
              onChange={(e) => setSnapshotName(e.target.value)}
              placeholder="Snapshot name..."
              className="bg-zinc-800 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 border border-zinc-700 focus:outline-none focus:border-cyan-600 w-64"
            />
            <button
              onClick={handleSaveSnapshot}
              disabled={!snapshotName.trim()}
              className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-lg disabled:opacity-30 transition-colors"
            >
              Save Snapshot
            </button>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 text-sm bg-cyan-700 hover:bg-cyan-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
