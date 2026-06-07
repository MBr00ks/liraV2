export default function AudioControls({
  ttsEnabled,
  reactionsEnabled,
  pauseMultiplier,
  debugMode,
  onTtsToggle,
  onReactionsToggle,
  onPauseChange,
  onDebugToggle,
}: {
  ttsEnabled: boolean;
  reactionsEnabled: boolean;
  pauseMultiplier: number;
  debugMode: boolean;
  onTtsToggle: () => void;
  onReactionsToggle: () => void;
  onPauseChange: (v: number) => void;
  onDebugToggle: () => void;
}) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
        Audio & Dev
      </h3>

      <label className="flex items-center justify-between text-sm">
        <span className="text-zinc-300">TTS</span>
        <input
          type="checkbox"
          checked={ttsEnabled}
          onChange={onTtsToggle}
          className="accent-cyan-600"
        />
      </label>

      <label className="flex items-center justify-between text-sm">
        <span className="text-zinc-300">Reactions</span>
        <input
          type="checkbox"
          checked={reactionsEnabled}
          onChange={onReactionsToggle}
          className="accent-cyan-600"
        />
      </label>

      <div className="space-y-1">
        <div className="flex justify-between text-sm text-zinc-400">
          <span>Pause</span>
          <span>{pauseMultiplier.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={pauseMultiplier}
          onChange={(e) => onPauseChange(parseFloat(e.target.value))}
          className="w-full accent-cyan-600"
        />
      </div>

      <label className="flex items-center justify-between text-sm">
        <span className="text-zinc-300">Debug Panel</span>
        <input
          type="checkbox"
          checked={debugMode}
          onChange={onDebugToggle}
          className="accent-cyan-600"
        />
      </label>

      <div className="text-xs text-zinc-600 border-t border-zinc-800 pt-2 space-y-1">
        <label className="flex items-center justify-between">
          <span>Web Search</span>
          <span className="text-zinc-700">soon</span>
        </label>
        <label className="flex items-center justify-between">
          <span>Memory</span>
          <span className="text-zinc-700">soon</span>
        </label>
      </div>
    </div>
  );
}
