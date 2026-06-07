import { useState, useEffect } from "react";

interface LogSession {
  session_id: string;
  file: string;
  message_count: number;
  timestamp: string;
}

interface LogMessage {
  role: string;
  content: string;
  timestamp: string;
  mode?: string;
  model?: string;
}

export default function LogsPanel() {
  const [sessions, setSessions] = useState<LogSession[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<LogMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = async () => {
    try {
      const resp = await fetch("/api/logs");
      const data = await resp.json();
      setSessions(data.sessions || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchSessions(); }, []);

  const loadSession = async (sessionId: string) => {
    setSelected(sessionId);
    setLoading(true);
    try {
      const resp = await fetch(`/api/logs/${sessionId}`);
      const data = await resp.json();
      setMessages(data.messages || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const formatDate = (iso: string) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
        Logs
      </h3>

      {sessions.length === 0 ? (
        <p className="text-xs text-zinc-600">No conversations logged yet.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => loadSession(s.session_id)}
              className={`w-full text-left rounded-lg px-3 py-2 transition-colors ${
                selected === s.session_id
                  ? "bg-cyan-800/50 border border-cyan-700"
                  : "bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-800"
              }`}
            >
              <div className="text-sm text-zinc-200 truncate">
                {formatDate(s.timestamp) || s.session_id}
              </div>
              <div className="text-xs text-zinc-600">
                {s.message_count} messages
              </div>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <div className="border-t border-zinc-800 pt-3 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-medium text-zinc-500 uppercase">
              {selected}
            </h4>
            <button
              onClick={() => { setSelected(null); setMessages([]); }}
              className="text-xs text-zinc-600 hover:text-zinc-400"
            >
              Close
            </button>
          </div>
          {loading ? (
            <p className="text-xs text-zinc-600">Loading...</p>
          ) : (
            <div className="max-h-64 overflow-y-auto space-y-2">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2 text-xs ${
                    m.role === "user"
                      ? "bg-cyan-900/30 border border-cyan-800/50 ml-4"
                      : "bg-zinc-800/50 border border-zinc-800 mr-4"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`font-medium ${m.role === "user" ? "text-cyan-300" : "text-zinc-300"}`}>
                      {m.role}
                    </span>
                    <span className="text-zinc-600">
                      {formatDate(m.timestamp)}
                    </span>
                  </div>
                  <div className="text-zinc-400 whitespace-pre-wrap break-words">
                    {m.content.length > 300
                      ? m.content.slice(0, 300) + "..."
                      : m.content}
                  </div>
                  {m.mode && (
                    <span className="text-[10px] text-zinc-600 mt-1 block">mode: {m.mode}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
