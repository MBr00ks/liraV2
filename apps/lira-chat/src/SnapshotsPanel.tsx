import { useState, useEffect } from "react";

interface SnapshotInfo {
  name: string;
  file: string;
  timestamp: string;
  modes: string[];
}

export default function SnapshotsPanel() {
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadStatus, setLoadStatus] = useState("");

  const fetchSnapshots = async () => {
    const resp = await fetch("/api/snapshots");
    const data = await resp.json();
    setSnapshots(data.snapshots);
  };

  useEffect(() => {
    fetchSnapshots();
  }, []);

  const handleLoad = async (file: string) => {
    setLoading(true);
    setLoadStatus("");
    try {
      const resp = await fetch("/api/snapshots/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setLoadStatus(`Loaded "${data.loaded}"`);
        // Refresh page to reflect loaded personalities
        setTimeout(() => window.location.reload(), 1500);
      } else {
        setLoadStatus(`Error: ${data.error}`);
      }
    } catch (err: any) {
      setLoadStatus(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
        Snapshots
      </h3>

      {snapshots.length === 0 ? (
        <p className="text-xs text-zinc-600">No snapshots yet.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {snapshots.map((s) => (
            <div
              key={s.file}
              className="flex items-center justify-between bg-zinc-800/50 rounded-lg px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <div className="text-sm text-zinc-200 truncate">{s.name}</div>
                <div className="text-xs text-zinc-600">
                  {s.timestamp} &middot; {s.modes.join(", ")}
                </div>
              </div>
              <button
                onClick={() => handleLoad(s.file)}
                disabled={loading}
                className="shrink-0 ml-2 px-2.5 py-1 text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded-md disabled:opacity-30 transition-colors"
              >
                Load
              </button>
            </div>
          ))}
        </div>
      )}

      {loadStatus && (
        <p className={`text-xs ${loadStatus.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
          {loadStatus}
        </p>
      )}
    </div>
  );
}
