import { useState } from "react";

export interface LoreEntry {
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

const ACT_LABELS: Record<string, string> = {
  always: "Core",
  mode: "Context",
  trigger: "On Trigger",
};

const ACT_LABEL_FULL: Record<string, string> = {
  always: "Core (always injected)",
  mode: "Context (mode match)",
  trigger: "On Trigger (keyword)",
};

export default function LorePanel({
  entries,
  activeMode,
  onToggleWorldbook,
  onEdit,
  onDeleteEntry,
  onDeleteWorldbook,
  onExportWorldbook,
  onMoveEntry,
  onMoveWorldbook,
  onQuickUpdate,
}: {
  entries: LoreEntry[];
  activeMode: string;
  onToggleWorldbook: (worldbook: string, mode: string, active: boolean) => void;
  onEdit: (entry: LoreEntry) => void;
  onDeleteEntry?: (entry: LoreEntry) => void;
  onDeleteWorldbook?: (worldbook: string) => void;
  onExportWorldbook?: (worldbook: string) => void;
  onMoveEntry?: (entryId: string, direction: "up" | "down") => void;
  onMoveWorldbook?: (worldbook: string, direction: "up" | "down") => void;
  onQuickUpdate?: (entryId: string, fields: Partial<LoreEntry>) => void;
}) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const filtered = entries.filter(
    (e) =>
      e.title.toLowerCase().includes(search.toLowerCase()) ||
      (e.source_worldbook || "").toLowerCase().includes(search.toLowerCase()) ||
      (e.trigger_keywords || []).some((k) =>
        k.toLowerCase().includes(search.toLowerCase())
      )
  );

  const byWorldbook: Record<string, LoreEntry[]> = {};
  for (const e of filtered) {
    const book = e.source_worldbook || "Ungrouped";
    if (!byWorldbook[book]) byWorldbook[book] = [];
    byWorldbook[book].push(e);
  }
  const worldbookNames = Object.keys(byWorldbook).sort();

  const toggleGroup = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const isModeActive = (e: LoreEntry) => e.modes?.includes(activeMode) ?? false;

  return (
    <div className="space-y-2">
      <input
        type="text"
        placeholder="Search lore..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-zinc-800 rounded px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 border border-zinc-700 focus:outline-none focus:border-cyan-600"
      />
      <div className="space-y-1 max-h-[60vh] overflow-y-auto">
        {worldbookNames.map((book, wbIdx) => {
          const bookEntries = byWorldbook[book];
          const isExpanded = expanded[book];
          const allActive = bookEntries.every(isModeActive);
          const isFirst = wbIdx === 0;
          const isLast = wbIdx === worldbookNames.length - 1;

          return (
            <div key={book} className="rounded-lg border border-zinc-800 overflow-hidden">
              {/* Worldbook header */}
              <div className="flex items-center bg-zinc-800/50 hover:bg-zinc-800 transition-colors">
                <label className="flex items-center pl-2 pr-1 py-2 cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    checked={allActive}
                    onChange={() => onToggleWorldbook(book, activeMode, !allActive)}
                    className="accent-cyan-600"
                  />
                </label>
                {onMoveWorldbook && (
                  <div className="flex flex-col shrink-0 pr-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); onMoveWorldbook(book, "up"); }}
                      className={`text-xs leading-none ${isFirst ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                      disabled={isFirst}
                      title="Move up"
                    >{"\u25B2"}</button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onMoveWorldbook(book, "down"); }}
                      className={`text-xs leading-none ${isLast ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                      disabled={isLast}
                      title="Move down"
                    >{"\u25BC"}</button>
                  </div>
                )}
                <button
                  onClick={() => toggleGroup(book)}
                  className="flex-1 flex items-center gap-2 py-2 pr-1 text-left min-w-0"
                >
                  <span className="text-xs text-zinc-500 shrink-0">
                    {isExpanded ? "\u25BC" : "\u25B6"}
                  </span>
                  <span className="text-sm text-zinc-200 truncate">{book}</span>
                </button>
                <span className="text-xs text-zinc-600 shrink-0 mr-2">
                  {bookEntries.filter(isModeActive).length}/{bookEntries.length}
                </span>
                <div className="flex items-center gap-1 pr-2">
                  {onExportWorldbook && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onExportWorldbook(book); }}
                      className="text-xs bg-cyan-900/50 border border-cyan-800 text-cyan-400 hover:bg-cyan-800 hover:text-cyan-200 transition-colors rounded px-1.5 py-0.5"
                      title={`Export ${book}`}
                    >
                      {"\u2913"}
                    </button>
                  )}
                  {onDeleteWorldbook && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm(`Delete entire worldbook "${book}" (${bookEntries.length} entries)?`)) {
                          onDeleteWorldbook(book);
                        }
                      }}
                      className="text-xs bg-red-900/30 border border-red-800 text-red-400 hover:bg-red-800 hover:text-red-200 transition-colors rounded px-1.5 py-0.5"
                      title={`Delete ${book}`}
                    >
                      {"\uD83D\uDDD1"}
                    </button>
                  )}
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
                        className="flex items-center gap-2 pl-2 py-1.5 hover:bg-zinc-800/30"
                      >
                        {/* Move arrows — always visible */}
                        {onMoveEntry && (
                          <div className="flex flex-col shrink-0">
                            <button
                              onClick={() => onMoveEntry(e.id, "up")}
                              className={`text-xs leading-none ${entryFirst ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                              disabled={entryFirst}
                              title="Move up"
                            >{"\u25B2"}</button>
                            <button
                              onClick={() => onMoveEntry(e.id, "down")}
                              className={`text-xs leading-none ${entryLast ? "text-zinc-800" : "text-zinc-500 hover:text-zinc-200"}`}
                              disabled={entryLast}
                              title="Move down"
                            >{"\u25BC"}</button>
                          </div>
                        )}
                        {/* Enabled toggle */}
                        {onQuickUpdate && (
                          <input
                            type="checkbox"
                            checked={e.enabled}
                            onChange={() => onQuickUpdate(e.id, { enabled: !e.enabled })}
                            className="accent-green-600 shrink-0 cursor-pointer"
                            title={e.enabled ? "Disable" : "Enable"}
                          />
                        )}
                        {/* Activation select */}
                        {onQuickUpdate ? (
                          <select
                            value={e.activation}
                            onChange={(ev) => onQuickUpdate(e.id, { activation: ev.target.value })}
                            onClick={(ev) => ev.stopPropagation()}
                            className="bg-zinc-800 text-[10px] text-zinc-400 rounded px-1 py-0.5 border border-zinc-700 shrink-0 cursor-pointer"
                            title={ACT_LABEL_FULL[e.activation]}
                          >
                            <option value="always">{ACT_LABELS.always}</option>
                            <option value="mode">{ACT_LABELS.mode}</option>
                            <option value="trigger">{ACT_LABELS.trigger}</option>
                          </select>
                        ) : (
                          <span className="text-[10px] text-zinc-600 shrink-0 w-14 text-center">
                            {ACT_LABELS[e.activation] || e.activation}
                          </span>
                        )}
                        {/* Title */}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-zinc-200 truncate">
                            {e.title}
                            {isModeActive(e) && (
                              <span className="text-[10px] text-cyan-600 font-medium ml-1">ACTIVE</span>
                            )}
                          </div>
                        </div>
                        {/* Action buttons — always visible */}
                        <div className="flex items-center gap-1 pr-2">
                          <button
                            onClick={() => onEdit(e)}
                            className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors shrink-0 px-1"
                            title="Edit"
                          >
                            {"\u270E"}
                          </button>
                          {onDeleteEntry && (
                            <button
                              onClick={() => {
                                if (window.confirm(`Delete "${e.title}"?`)) onDeleteEntry(e);
                              }}
                              className="text-xs text-zinc-500 hover:text-red-400 transition-colors shrink-0 px-1"
                              title="Delete"
                            >
                              {"\uD83D\uDDD1"}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
