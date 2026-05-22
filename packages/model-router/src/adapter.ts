import { ChatMessage, ChatResponse, StreamChunk, EmbeddingResponse } from "./types";

export interface LLMAdapterInterface {
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatResponse>;

  streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncGenerator<StreamChunk, void, unknown>;

  embed(text: string, options?: EmbedOptions): Promise<EmbeddingResponse>;

  healthCheck(): Promise<boolean>;

  getModelName(): string;

  getProviderName(): string;
}

export interface ChatOptions {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  stop?: string[];
  stream?: boolean;
}

export interface EmbedOptions {
  model?: string;
}
