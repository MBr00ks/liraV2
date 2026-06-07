import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import WebSocketProvider from './WebSocketProvider'
import ChatPage from './ChatPage'
import LorePage from './LorePage'
import { Routes, Route } from 'react-router-dom'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <WebSocketProvider>
        <Routes>
          <Route element={<App />}>
            <Route index element={<ChatPage />} />
            <Route path="lore" element={<LorePage />} />
          </Route>
        </Routes>
      </WebSocketProvider>
    </BrowserRouter>
  </StrictMode>,
)
