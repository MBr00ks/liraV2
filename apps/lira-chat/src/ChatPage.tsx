import { useMemo } from "react";
import ChatView from "./ChatView";
import MessageInput from "./MessageInput";
import SnapshotsPanel from "./SnapshotsPanel";
import AudioControls from "./AudioControls";
import LogsPanel from "./LogsPanel";
import DebugPanel from "./DebugPanel";
import { useWs } from "./WebSocketProvider";

export default function ChatPage() {
  const {
    messages, connected, handleSend, handleInterrupt,
    ttsEnabled, reactionsEnabled, pauseMultiplier, debugVisible,
    setTtsEnabled, setReactionsEnabled, setPauseMultiplier, setDebugVisible,
    systemPreview, injectedLore,
    handleCopy, handleDeleteMessage, handleRetry,
  } = useWs();

  return useMemo(() => (
    <>
      <div className="flex h-full overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <ChatView messages={messages} onInterrupt={handleInterrupt}
            onCopy={handleCopy} onDelete={handleDeleteMessage} onRetry={handleRetry} />
          <div className="p-4 border-t border-zinc-800">
            <MessageInput onSend={handleSend} disabled={!connected} />
          </div>
        </div>
        <aside className="w-80 border-l border-zinc-800 bg-zinc-900 p-4 flex flex-col gap-6 overflow-y-auto shrink-0">
          <AudioControls
            ttsEnabled={ttsEnabled}
            reactionsEnabled={reactionsEnabled}
            pauseMultiplier={pauseMultiplier}
            debugMode={debugVisible}
            onTtsToggle={() => setTtsEnabled(!ttsEnabled)}
            onReactionsToggle={() => setReactionsEnabled(!reactionsEnabled)}
            onPauseChange={setPauseMultiplier}
            onDebugToggle={() => setDebugVisible(!debugVisible)}
          />
          <SnapshotsPanel />
          <LogsPanel />
        </aside>
      </div>
      <DebugPanel
        systemPreview={systemPreview}
        injectedLore={injectedLore}
        visible={debugVisible}
      />
    </>
  ), [messages, connected, handleSend, handleInterrupt,
      ttsEnabled, reactionsEnabled, pauseMultiplier, debugVisible,
      setTtsEnabled, setReactionsEnabled, setPauseMultiplier, setDebugVisible,
      systemPreview, injectedLore]);
}
