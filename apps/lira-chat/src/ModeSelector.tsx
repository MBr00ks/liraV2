const MODES = ["assistant", "companion", "observer"];

export default function ModeSelector({
  active,
  onChange,
}: {
  active: string;
  onChange: (mode: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 bg-zinc-800 rounded-lg p-1">
      {MODES.map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
            active === m
              ? "bg-cyan-600 text-white"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          {m.charAt(0).toUpperCase() + m.slice(1)}
        </button>
      ))}
    </div>
  );
}
