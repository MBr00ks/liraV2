import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import App from "./App.tsx";
import ChatPage from "./ChatPage";
import LorePage from "./LorePage";
import { ToastProvider } from "./providers/ToastProvider";
import { AudioProvider } from "./providers/AudioProvider";
import { ChatProvider } from "./providers/ChatProvider";
import WebSocketProvider from "./WebSocketProvider";
import { createWebSocketTransport } from "./transport/WebSocketTransport";

const transport = createWebSocketTransport();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <AudioProvider>
          <ChatProvider transport={transport}>
            <WebSocketProvider transport={transport}>
              <Routes>
                <Route element={<App />}>
                  <Route index element={<ChatPage />} />
                  <Route path="lore" element={<LorePage />} />
                </Route>
              </Routes>
            </WebSocketProvider>
          </ChatProvider>
        </AudioProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
);
