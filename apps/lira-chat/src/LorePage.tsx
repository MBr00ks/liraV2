import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import LoreCreator from "./LoreCreator";
import ModeSelector from "./ModeSelector";
import type { LoreEntry } from "./LorePanel";
import { useWs } from "./WebSocketProvider";

const ACT_LABELS: Record<string, string> = {
  always: "Core",
  mode: "Context",
  trigger: "On Trigger",
};

export default function LorePage() {
  const navigate = useNavigate();
  const { loreEntries, handleToggleWorldbook, handleEdit, handleRefreshLore,
    handleDeleteWorldbook, handleExportWorldbook,
    handleMoveEntry, handleMoveWorldbook, handleQuickUpdate } = useWs();
  const [tab, setTab] = useState<"browse" | "create" | "search">("browse");
  const [loreMode, setLoreMode] = useState(() => {
    try { return localStorage.getItem("lira_lore_mode") || "assistant"; } catch { return "assistant"; }
  });
  useEffect(() => { try { localStorage.setItem("lira_lore_mode", loreMode); } catch { /* ignore */ } }, [loreMode]);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [importStatus, setImportStatus] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isModeActive = (e: LoreEntry) => e.modes?.includes(loreMode) ?? false;

  const { groups, ordered } = useMemo(() => {
    const byWorldbook: Record<string, { entries: LoreEntry[] }> = {};
    for (const e of loreEntries) {
      const book = e.source_worldbook || "Ungrouped";
      if (!byWorldbook[book]) byWorldbook[book] = { entries: [] };
      byWorldbook[book].entries.push(e);
    }
    const ordered = Object.keys(byWorldbook);
    return { groups: byWorldbook, ordered };
  }, [loreEntries]);

  const toggleGroup = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const searchResults = useMemo(() => {
    if (!search.trim()) return [];
    const q = search.toLowerCase();
    return loreEntries.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.content.toLowerCase().includes(q) ||
        (e.source_worldbook || "").toLowerCase().includes(q) ||
        (e.trigger_keywords || []).some((k) => k.toLowerCase().includes(q))
    );
  }, [loreEntries, search]);

  const handleExport = async () => {
    const resp = await fetch("/api/lore/export");
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lore-export.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportStatus("");
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      let entries = data.entries;

      // Detect SillyTavern format (entries is an object keyed by index)
      if (entries && !Array.isArray(entries)) {
        const wbName = data.name || "Imported";
        entries = Object.values(entries).map((e: any) => ({
          id: String(e.uid ?? e.id ?? ""),
          title: e.comment || e.title || "Untitled",
          content: e.content || "",
          enabled: !e.disable,
          activation: e.constant ? "always" : "trigger",
          modes: [],
          trigger_keywords: e.key || e.trigger_keywords || [],
          source_worldbook: e.group || wbName,
          priority: e.order ?? e.priority ?? 0,
        }));
      }

      if (!entries || entries.length === 0) {
        setImportStatus("Error: No entries found in file");
        return;
      }

      const resp = await fetch("/api/lore/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries: Array.isArray(entries) ? entries : [] }),
      });
      const result = await resp.json();
      if (resp.ok) {
        setImportStatus(`Imported ${result.imported} entries`);
        handleRefreshLore();
      } else {
        setImportStatus(`Error: ${result.error}`);
      }
    } catch (err: any) {
      setImportStatus(`Error: ${err.message}`);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const confirmDelete = (entry: LoreEntry) => {
    if (window.confirm(`Delete "${entry.title}"?`)) {
      fetch(`/api/lore/entry/${entry.id}`, { method: "DELETE" }).then(() => handleRefreshLore());
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-zinc-800 bg-zinc-900 shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-zinc-100">Lore Manager</h2>
          <div className="flex items-center gap-1 bg-zinc-800 rounded-lg p-0.5">
            {(["browse", "create", "search"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1 text-sm rounded-md transition-colors capitalize ${
                  tab === t
                    ? "bg-cyan-700 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <span className="text-xs text-zinc-600 mx-1">editing for:</span>
          <ModeSelector active={loreMode} onChange={setLoreMode} />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 rounded border border-zinc-700 hover:border-zinc-500 transition-colors"
          >
            Export All
          </button>
          <label className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 rounded border border-zinc-700 hover:border-zinc-500 transition-colors cursor-pointer">
            Import
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleImport}
              className="hidden"
            />
          </label>
          <button
            onClick={() => navigate("/")}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 rounded border border-zinc-700 hover:border-zinc-500 transition-colors"
          >
            Back
          </button>
        </div>
      </div>

      {importStatus && (
        <div className={`px-6 py-2 text-sm ${importStatus.startsWith("Error") ? "bg-red-950 text-red-400" : "bg-green-950 text-green-400"}`}>
          {importStatus}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        {tab === "browse" && (
          <div className="max-w-3xl mx-auto space-y-2">
            {ordered.map((book, wbIdx) => {
              const bookEntries = groups[book].entries;
              const isExpanded = expanded[book];
              const allActive = bookEntries.every(isModeActive);
              const activeCount = bookEntries.filter(isModeActive).length;
              const isFirst = wbIdx === 0;
              const isLast = wbIdx === ordered.length - 1;

              return (
                <div key={book} className="rounded-lg border border-zinc-800 overflow-hidden">
                  <div className="flex items-center bg-zinc-800/50 hover:bg-zinc-800 transition-colors">
                    <label className="flex items-center pl-3 pr-2 py-3 cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={allActive}
                        onChange={() => handleToggleWorldbook(book, loreMode, !allActive)}
                        className="accent-cyan-600"
                      />
                    </label>
                    {handleMoveWorldbook && (
                      <div className="flex flex-col shrink-0 pr-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleMoveWorldbook(book, "up"); }}
                          className={`text-xs leading-none ${isFirst ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                          disabled={isFirst}
                          title="Move up"
                        >{"\u25B2"}</button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleMoveWorldbook(book, "down"); }}
                          className={`text-xs leading-none ${isLast ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                          disabled={isLast}
                          title="Move down"
                        >{"\u25BC"}</button>
                      </div>
                    )}
                    <button
                      onClick={() => toggleGroup(book)}
                      className="flex-1 flex items-center gap-2 py-3 text-left min-w-0"
                    >
                      <span className="text-sm text-zinc-500 shrink-0">
                        {isExpanded ? "\u25BC" : "\u25B6"}
                      </span>
                      <span className="text-base text-zinc-200 truncate font-medium">{book}</span>
                    </button>
                    <div className="flex items-center gap-2 shrink-0 mr-3">
                      <span className="text-xs text-zinc-500">
                        {activeCount}/{bookEntries.length}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleExportWorldbook(book); }}
                        className="text-xs bg-cyan-900/50 border border-cyan-800 text-cyan-400 hover:bg-cyan-800 hover:text-cyan-200 transition-colors rounded px-1.5 py-0.5"
                        title={`Export ${book}`}
                      >
                        {"\u2913"}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Delete entire worldbook "${book}" (${bookEntries.length} entries)?`)) {
                            handleDeleteWorldbook(book);
                          }
                        }}
                        className="text-xs bg-red-900/30 border border-red-800 text-red-400 hover:bg-red-800 hover:text-red-200 transition-colors rounded px-1.5 py-0.5"
                        title={`Delete ${book}`}
                      >
                        {"\uD83D\uDDD1"}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="divide-y divide-zinc-800">
                      {bookEntries.map((e, entryIdx) => {
                        const entryFirst = entryIdx === 0;
                        const entryLast = entryIdx === bookEntries.length - 1;
                        return (
                          <div
                            key={e.id}
                            className="flex items-center gap-3 pl-3 py-2.5 hover:bg-zinc-800/30"
                          >
                            {handleMoveEntry && (
                              <div className="flex flex-col shrink-0">
                                <button
                                  onClick={() => handleMoveEntry(e.id, "up")}
                                  className={`text-xs leading-none ${entryFirst ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                                  disabled={entryFirst}
                                  title="Move up"
                                >{"\u25B2"}</button>
                                <button
                                  onClick={() => handleMoveEntry(e.id, "down")}
                                  className={`text-xs leading-none ${entryLast ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                                  disabled={entryLast}
                                  title="Move down"
                                >{"\u25BC"}</button>
                              </div>
                            )}
                            {handleQuickUpdate && (
                              <input
                                type="checkbox"
                                checked={e.enabled}
                                onChange={() => handleQuickUpdate(e.id, { enabled: !e.enabled })}
                                className="accent-green-600 shrink-0 cursor-pointer"
                                title={e.enabled ? "Disable" : "Enable"}
                              />
                            )}
                            {handleQuickUpdate ? (
                              <select
                                value={e.activation}
                                onChange={(ev) => handleQuickUpdate(e.id, { activation: ev.target.value })}
                                className="bg-zinc-800 text-xs text-zinc-400 rounded px-1.5 py-0.5 border border-zinc-700 shrink-0 cursor-pointer"
                              >
                                <option value="always">{ACT_LABELS.always}</option>
                                <option value="mode">{ACT_LABELS.mode}</option>
                                <option value="trigger">{ACT_LABELS.trigger}</option>
                              </select>
                            ) : (
                              <span className="text-xs text-zinc-600 shrink-0">{ACT_LABELS[e.activation] || e.activation}</span>
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-zinc-200 truncate">{e.title}</span>
                                {isModeActive(e) && (
                                  <span className="text-[10px] text-cyan-600 font-medium bg-cyan-950 px-1.5 py-0.5 rounded">ACTIVE</span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-zinc-600 mt-0.5">
                                {e.activation === "trigger" && e.trigger_keywords && e.trigger_keywords.length > 0 && (
                                  <span>
                                    [{e.trigger_keywords.slice(0, 3).join(", ")}
                                    {e.trigger_keywords.length > 3 ? "..." : ""}]
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 pr-3">
                              <button
                                onClick={() => handleEdit(e)}
                                className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors shrink-0 px-1"
                                title="Edit entry"
                              >
                                {"\u270E"}
                              </button>
                              <button
                                onClick={() => confirmDelete(e)}
                                className="text-xs text-zinc-500 hover:text-red-400 transition-colors shrink-0 px-1"
                                title="Delete entry"
                              >
                                {"\u2715"}
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {loreEntries.length === 0 && (
              <p className="text-center text-zinc-600 py-12">No lore entries yet.</p>
            )}
          </div>
        )}

        {tab === "create" && (
          <div className="max-w-lg mx-auto pt-4">
            <LoreCreator
              onCreated={() => {
                handleRefreshLore();
                setTab("browse");
              }}
              onClose={() => setTab("browse")}
              inline
            />
          </div>
        )}

        {tab === "search" && (
          <div className="max-w-3xl mx-auto space-y-4">
            <input
              type="text"
              placeholder="Search across all lore entries..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-800 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 border border-zinc-700 focus:outline-none focus:border-cyan-600"
              autoFocus
            />
            <div className="space-y-2">
              {searchResults.map((e) => (
                <div
                  key={e.id}
                  className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 hover:bg-zinc-800/50"
                >
                  {handleMoveEntry && (
                    <div className="flex flex-col shrink-0">
                      <button
                        onClick={() => handleMoveEntry(e.id, "up")}
                        className="text-xs leading-none text-zinc-500 hover:text-zinc-200"
                        title="Move up"
                      >{"\u25B2"}</button>
                      <button
                        onClick={() => handleMoveEntry(e.id, "down")}
                        className="text-xs leading-none text-zinc-500 hover:text-zinc-200"
                        title="Move down"
                      >{"\u25BC"}</button>
                    </div>
                  )}
                  {handleQuickUpdate && (
                    <input
                      type="checkbox"
                      checked={e.enabled}
                      onChange={() => handleQuickUpdate(e.id, { enabled: !e.enabled })}
                      className="accent-green-600 shrink-0 cursor-pointer"
                      title={e.enabled ? "Disable" : "Enable"}
                    />
                  )}
                  {handleQuickUpdate ? (
                    <select
                      value={e.activation}
                      onChange={(ev) => handleQuickUpdate(e.id, { activation: ev.target.value })}
                      className="bg-zinc-800 text-xs text-zinc-400 rounded px-1.5 py-0.5 border border-zinc-700 shrink-0 cursor-pointer"
                    >
                      <option value="always">{ACT_LABELS.always}</option>
                      <option value="mode">{ACT_LABELS.mode}</option>
                      <option value="trigger">{ACT_LABELS.trigger}</option>
                    </select>
                  ) : (
                    <span className="text-xs text-zinc-600 shrink-0">{ACT_LABELS[e.activation] || e.activation}</span>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-zinc-200 font-medium truncate">{e.title}</span>
                      {isModeActive(e) && (
                        <span className="text-[10px] text-cyan-600 font-medium">ACTIVE</span>
                      )}
                    </div>
                    <div className="text-xs text-zinc-600 mt-0.5">
                      {e.source_worldbook}
                    </div>
                    <div className="text-xs text-zinc-500 mt-1 line-clamp-2">{e.content}</div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEdit(e)}
                      className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors shrink-0 px-1"
                    >
                      {"\u270E"}
                    </button>
                    <button
                      onClick={() => confirmDelete(e)}
                      className="text-xs text-zinc-500 hover:text-red-400 transition-colors shrink-0 px-1"
                    >
                      {"\u2715"}
                    </button>
                  </div>
                </div>
              ))}
              {search.trim() && searchResults.length === 0 && (
                <p className="text-center text-zinc-600 py-8">No results for &ldquo;{search}&rdquo;</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
