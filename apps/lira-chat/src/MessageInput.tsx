import { useState, useRef, useCallback } from "react";

// Build a WAV blob from raw PCM samples
function buildWav(samples: Float32Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * bitsPerSample / 8;
  const blockAlign = numChannels * bitsPerSample / 8;
  const dataSize = samples.length * blockAlign;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // WAV header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  // Write samples as int16
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

export default function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);

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
      const ctx = new AudioContext({ sampleRate: 16000 });
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      chunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        chunksRef.current.push(new Float32Array(input));
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      streamRef.current = stream;
      ctxRef.current = ctx;
      processorRef.current = processor;
      setRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    setRecording(false);
    const ctx = ctxRef.current;
    const stream = streamRef.current;
    const processor = processorRef.current;

    if (processor) {
      processor.disconnect();
      processor.onaudioprocess = null;
    }
    if (stream) stream.getTracks().forEach((t) => t.stop());

    // Build WAV from collected chunks
    const totalLength = chunksRef.current.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunksRef.current) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    if (totalLength > 0) {
      const wav = buildWav(merged, ctx?.sampleRate || 16000);
      const form = new FormData();
      form.append("file", wav, "voice.wav");
      try {
        const resp = await fetch("/api/transcribe", { method: "POST", body: form });
        const data = await resp.json();
        if (data.text) onSend(data.text);
      } catch (err) {
        console.error("Transcription failed:", err);
      }
    }

    if (ctx) ctx.close();
  }, [onSend]);

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
