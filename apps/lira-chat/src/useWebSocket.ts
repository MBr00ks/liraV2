export type WSMessage =
  | { type: "text"; delta: string }
  | { type: "audio"; chunk: string; seq?: number }
  | { type: "done"; full_text: string }
  | { type: "error"; message: string }
  | { type: "lore_injected"; lore: any[]; system_preview: string }
  | { type: "lore_list"; entries: any[] }
  | { type: "lore_toggled"; entry: any }
  | { type: "lore_updated"; entry: any }
  | { type: "worldbook_toggled"; worldbook: string; mode: string; active: boolean }
  | { type: "mode_set"; mode: string }
  | { type: "system_set" }
  | { type: "history_cleared" }
  | { type: "tts_error"; message: string }
  | { type: "image"; data: string; filename: string; prompt: string };

export type SendMessage =
  | { type: "message"; text: string }
  | { type: "set_mode"; mode: string }
  | { type: "set_system"; text: string }
  | { type: "get_lore" }
  | { type: "clear_history" }
  | { type: "toggle_lore"; id: string; mode?: string }
  | { type: "toggle_worldbook"; worldbook: string; mode: string; active: boolean }
  | { type: "update_lore"; entry: any };

export function createWs(
  onMessage: (msg: WSMessage) => void,
  onOpen?: () => void,
  onClose?: () => void,
): WebSocket {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${location.host}/ws`;
  const ws = new WebSocket(url);

  ws.onopen = () => onOpen?.();
  ws.onclose = () => onClose?.();
  ws.onmessage = (event) => {
    try {
      const msg: WSMessage = JSON.parse(event.data);
      onMessage(msg);
    } catch { /* ignore */ }
  };
  return ws;
}
