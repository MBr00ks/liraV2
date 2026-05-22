import { LLMAdapterInterface, ChatOptions } from "./adapter";
import { ChatMessage, ChatResponse, StreamChunk, EmbeddingResponse, ModelProvider } from "./types";

interface OllamaChatPayload {
  model: string;
  messages: Array<{ role: string; content: string }>;
  stream: boolean;
  options?: {
    temperature?: number;
    num_predict?: number;
    top_p?: number;
    stop?: string[];
  };
}

interface OllamaEmbedPayload {
  model: string;
  prompt: string;
}

interface OllamaChatResponse {
  message: { role: string; content: string };
  done: boolean;
  done_reason?: string;
  total_duration?: number;
  prompt_eval_count?: number;
  eval_count?: number;
}

interface OllamaStreamResponse {
  message: { role: string; content: string };
  done: boolean;
  done_reason?: string;
}

interface OllamaEmbedResponse {
  embedding: number[];
}

export class OllamaClient implements LLMAdapterInterface {
  private readonly baseUrl: string;
  private readonly defaultModel: string;

  constructor(baseUrl: string = "http://localhost:11434", defaultModel: string = "qwen3:32b") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.defaultModel = defaultModel;
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatResponse> {
    const payload: OllamaChatPayload = {
      model: this.defaultModel,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: false,
      options: {
        temperature: options?.temperature,
        num_predict: options?.max_tokens,
        top_p: options?.top_p,
        stop: options?.stop,
      },
    };

    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Ollama chat failed: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as OllamaChatResponse;

    return {
      content: data.message.content,
      model: this.defaultModel,
      provider: "ollama" as ModelProvider,
      usage: {
        prompt_tokens: data.prompt_eval_count ?? 0,
        completion_tokens: data.eval_count ?? 0,
        total_tokens: (data.prompt_eval_count ?? 0) + (data.eval_count ?? 0),
      },
      finish_reason: data.done_reason ?? "stop",
    };
  }

  async *streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncGenerator<StreamChunk, void, unknown> {
    const payload: OllamaChatPayload = {
      model: this.defaultModel,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: true,
      options: {
        temperature: options?.temperature,
        num_predict: options?.max_tokens,
        top_p: options?.top_p,
        stop: options?.stop,
      },
    };

    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Ollama stream chat failed: ${response.status} ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error("Ollama stream response has no body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.trim() === "") continue;
          try {
            const parsed = JSON.parse(line) as OllamaStreamResponse;
            yield {
              content: parsed.message.content,
              done: parsed.done,
              model: this.defaultModel,
              provider: "ollama" as ModelProvider,
            };
            if (parsed.done) return;
          } catch {
            // Skip malformed lines
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async embed(text: string, options?: { model?: string }): Promise<EmbeddingResponse> {
    const model = options?.model ?? process.env.OLLAMA_EMBEDDING_MODEL ?? "nomic-embed-text";

    const payload: OllamaEmbedPayload = {
      model,
      prompt: text,
    };

    const response = await fetch(`${this.baseUrl}/api/embed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Ollama embed failed: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as OllamaEmbedResponse;

    return {
      embedding: data.embedding,
      model,
      provider: "ollama" as ModelProvider,
    };
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  getModelName(): string {
    return this.defaultModel;
  }

  getProviderName(): string {
    return "ollama";
  }
}
