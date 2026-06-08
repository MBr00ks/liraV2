import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from "react";

export interface ToastMsg {
  id: number;
  text: string;
  type: "error" | "info" | "success";
}

interface ToastContextValue {
  toasts: ToastMsg[];
  pushToast: (text: string, type?: ToastMsg["type"]) => void;
  removeToast: (id: number) => void;
}

const Ctx = createContext<ToastContextValue | null>(null);

export function useToasts() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useToasts must be inside ToastProvider");
  return c;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const toastId = useRef(0);

  const pushToast = useCallback((text: string, type: ToastMsg["type"] = "info") => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, text, type }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <Ctx.Provider value={{ toasts, pushToast, removeToast }}>
      {children}
    </Ctx.Provider>
  );
}
