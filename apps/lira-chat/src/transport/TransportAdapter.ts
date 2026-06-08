/** Transport layer abstraction — swap WebSocket for NATS/SSE without changing components. */


export type IncomingMessage =
  | { type: "text"; delta: string }
  | { type: "audio"; chunk: string; seq?: number }
  | { type: "done"; full_text: string }
  | { type: "error"; message: string }
  | { type: "lore_injected"; lore: unknown[]; system_preview: string }
  | { type: "lore_list"; entries: unknown[] }
  | { type: "lore_toggled"; entry: unknown }
  | { type: "lore_updated"; entry: unknown }
  | { type: "worldbook_toggled"; worldbook: string; mode: string; active: boolean }
  | { type: "mode_set"; mode: string }
  | { type: "system_set" }
  | { type: "history_cleared" }
  | { type: "tts_error"; message: string }
  | { type: "image"; data: string; filename: string; prompt: string };

export type OutgoingMessage =
  | { type: "message"; text: string }
  | { type: "set_mode"; mode: string }
  | { type: "set_system"; text: string }
  | { type: "get_lore" }
  | { type: "clear_history" }
  | { type: "toggle_lore"; id: string; mode?: string }
  | { type: "toggle_worldbook"; worldbook: string; mode: string; active: boolean }
  | { type: "update_lore"; entry: unknown }
  | { type: "delete_message"; index: number };

export interface TransportAdapter {
  send(message: OutgoingMessage): void;
  onMessage(handler: (msg: IncomingMessage) => void): () => void;
  connect(): Promise<void>;
  disconnect(): void;
  readonly connected: boolean;
}
