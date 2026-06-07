import { useEffect } from "react";

export interface ToastMsg {
  id: number;
  text: string;
  type: "error" | "info" | "success";
}

export default function ErrorToast({
  toasts,
  onRemove,
}: {
  toasts: ToastMsg[];
  onRemove: (id: number) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-20 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onRemove={onRemove} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onRemove,
}: {
  toast: ToastMsg;
  onRemove: (id: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onRemove]);

  const colors = {
    error: "border-red-700 bg-red-950/90 text-red-200",
    info: "border-cyan-700 bg-cyan-950/90 text-cyan-200",
    success: "border-green-700 bg-green-950/90 text-green-200",
  };

  return (
    <div
      className={`px-4 py-3 rounded-lg border text-sm shadow-lg backdrop-blur-sm cursor-pointer ${colors[toast.type]}`}
      onClick={() => onRemove(toast.id)}
    >
      {toast.text}
    </div>
  );
}
