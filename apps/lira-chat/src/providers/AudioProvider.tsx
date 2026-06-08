import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface AudioContextValue {
  ttsEnabled: boolean;
  reactionsEnabled: boolean;
  pauseMultiplier: number;
  debugVisible: boolean;
  setTtsEnabled: (v: boolean) => void;
  setReactionsEnabled: (v: boolean) => void;
  setPauseMultiplier: (v: number) => void;
  setDebugVisible: (v: boolean) => void;
}

const Ctx = createContext<AudioContextValue | null>(null);

export function useAudio() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAudio must be inside AudioProvider");
  return c;
}

export function AudioProvider({ children }: { children: ReactNode }) {
  const [ttsEnabled, setTtsEnabled] = useState(() => {
    try { return localStorage.getItem("lira_tts") !== "false"; } catch { return true; }
  });
  const [reactionsEnabled, setReactionsEnabled] = useState(() => {
    try { return localStorage.getItem("lira_reactions") !== "false"; } catch { return true; }
  });
  const [pauseMultiplier, setPauseMultiplier] = useState(() => {
    try { const v = localStorage.getItem("lira_pause"); return v ? parseFloat(v) : 1.0; } catch { return 1.0; }
  });
  const [debugVisible, setDebugVisible] = useState(false);

  useEffect(() => { try { localStorage.setItem("lira_tts", String(ttsEnabled)); } catch { console.warn("AudioProvider: localStorage unavailable"); } }, [ttsEnabled]);
  useEffect(() => { try { localStorage.setItem("lira_reactions", String(reactionsEnabled)); } catch { console.warn("AudioProvider: localStorage unavailable"); } }, [reactionsEnabled]);
  useEffect(() => { try { localStorage.setItem("lira_pause", String(pauseMultiplier)); } catch { console.warn("AudioProvider: localStorage unavailable"); } }, [pauseMultiplier]);

  return (
    <Ctx.Provider value={{
      ttsEnabled, reactionsEnabled, pauseMultiplier, debugVisible,
      setTtsEnabled, setReactionsEnabled, setPauseMultiplier, setDebugVisible,
    }}>
      {children}
    </Ctx.Provider>
  );
}
