import type { TransportAdapter, IncomingMessage, OutgoingMessage } from "./TransportAdapter";

export function createWebSocketTransport(
  onStateChange?: (connected: boolean) => void,
): TransportAdapter {
  let ws: WebSocket | null = null;
  let handlers: Array<(msg: IncomingMessage) => void> = [];
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

  function connect(): Promise<void> {
    return new Promise((resolve) => {
      ws?.close();
      clearTimeout(reconnectTimer);

      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${protocol}//${location.host}/ws`;
      const socket = new WebSocket(url);

      socket.onopen = () => {
        ws = socket;
        onStateChange?.(true);
        resolve();
      };

      socket.onclose = () => {
        if (ws !== socket) return;
        ws = null;
        onStateChange?.(false);
        reconnectTimer = setTimeout(() => connect(), 2000);
      };

      socket.onmessage = (event) => {
        try {
          const msg: IncomingMessage = JSON.parse(event.data);
          for (const h of handlers) h(msg);
        } catch { /* ignore */ }
      };
    });
  }

  function disconnect(): void {
    clearTimeout(reconnectTimer);
    ws?.close();
    ws = null;
    onStateChange?.(false);
  }

  return {
    send(message: OutgoingMessage): void {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    },

    onMessage(handler: (msg: IncomingMessage) => void): () => void {
      handlers.push(handler);
      return () => { handlers = handlers.filter((h) => h !== handler); };
    },

    connect,
    disconnect,

    get connected(): boolean {
      return ws?.readyState === WebSocket.OPEN;
    },
  };
}
