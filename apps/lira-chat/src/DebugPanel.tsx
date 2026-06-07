export default function DebugPanel({
  systemPreview,
  injectedLore,
  visible,
}: {
  systemPreview: string;
  injectedLore: any[];
  visible: boolean;
}) {
  if (!visible) return null;

  return (
    <div className="bg-zinc-900 border-t border-zinc-700 p-4 space-y-3 text-xs font-mono max-h-[40vh] overflow-y-auto">
      <div>
        <h4 className="text-zinc-500 font-semibold uppercase tracking-wide mb-1">
          System Prompt (first 500 chars)
        </h4>
        <pre className="text-zinc-300 whitespace-pre-wrap">{systemPreview || "—"}</pre>
      </div>
      <div>
        <h4 className="text-zinc-500 font-semibold uppercase tracking-wide mb-1">
          Injected Lore ({injectedLore.length})
        </h4>
        {injectedLore.length === 0 && (
          <span className="text-zinc-600">No lore entries active</span>
        )}
        {injectedLore.map((l, i) => (
          <div key={i} className="mb-2">
            <span className="text-cyan-500">{l.title}</span>
            <p className="text-zinc-400">{l.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
