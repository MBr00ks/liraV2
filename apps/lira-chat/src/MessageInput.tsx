import { useState, useRef, useCallback } from "react";

export default function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const handleSubmit = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const input = (e.target as HTMLFormElement).querySelector("input")!;
      const text = input.value.trim();
      if (text) {
        onSend(text);
        input.value = "";
      }
    },
    [onSend]
  );

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        try {
          const resp = await fetch("/api/transcribe", { method: "POST", body: form });
          const data = await resp.json();
          if (data.text) onSend(data.text);
        } catch (err) {
          console.error("Transcription failed:", err);
        }
      };
      mediaRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
    }
  }, [onSend]);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
  }, []);

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <button
        type="button"
        onClick={recording ? stopRecording : startRecording}
        disabled={disabled}
        className={`rounded-lg px-3 py-2 font-medium transition-colors ${
          recording
            ? "bg-red-600 hover:bg-red-500 text-white"
            : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700"
        } disabled:opacity-50`}
        title={recording ? "Stop recording" : "Record voice"}
      >
        {recording ? "\u25A0" : "\u{1F3A4}"}
      </button>
      <input
        type="text"
        placeholder="Message Lira..."
        disabled={disabled}
        className="flex-1 bg-zinc-800 rounded-lg px-4 py-2 text-zinc-100 placeholder-zinc-500 border border-zinc-700 focus:outline-none focus:border-cyan-600 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled}
        className="bg-cyan-700 hover:bg-cyan-600 disabled:bg-zinc-700 text-white rounded-lg px-4 py-2 font-medium transition-colors"
      >
        Send
      </button>
    </form>
  );
}
