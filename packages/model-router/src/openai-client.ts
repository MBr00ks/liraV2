import OpenAI from "openai";
import { LLMAdapterInterface, ChatOptions } from "./adapter";
import { ChatMessage, ChatResponse, StreamChunk, EmbeddingResponse, ModelProvider } from "./types";

export class OpenAIClient implements LLMAdapterInterface {
  private readonly client: OpenAI;
  private readonly defaultModel: string;

  constructor(apiKey: string, baseUrl?: string, defaultModel: string = "gpt-4.1") {
    this.client = new OpenAI({ apiKey, ...(baseUrl && { baseURL: baseUrl }) });
    this.defaultModel = defaultModel;
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatResponse> {
    const response = await this.client.chat.completions.create({
      model: this.defaultModel,
      messages: messages as OpenAI.Chat.Completions.ChatCompletionMessageParam[],
      temperature: options?.temperature,
      max_tokens: options?.max_tokens,
      top_p: options?.top_p,
      stream: false,
    });

    const choice = response.choices[0];
    if (!choice?.message?.content) {
      throw new Error("OpenAI returned empty response");
    }

    return {
      content: choice.message.content,
      model: this.defaultModel,
      provider: "openai" as ModelProvider,
      usage: response.usage
        ? {
            prompt_tokens: response.usage.prompt_tokens,
            completion_tokens: response.usage.completion_tokens,
            total_tokens: response.usage.total_tokens,
          }
        : undefined,
      finish_reason: choice.finish_reason ?? "stop",
    };
  }

  async *streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncGenerator<StreamChunk, void, unknown> {
    const stream = await this.client.chat.completions.create({
      model: this.defaultModel,
      messages: messages as OpenAI.Chat.Completions.ChatCompletionMessageParam[],
      temperature: options?.temperature,
      max_tokens: options?.max_tokens,
      top_p: options?.top_p,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content ?? "";
      const done = chunk.choices[0]?.finish_reason !== null;

      yield {
        content,
        done,
        model: this.defaultModel,
        provider: "openai" as ModelProvider,
      };

      if (done) return;
    }
  }

  async embed(text: string, options?: { model?: string }): Promise<EmbeddingResponse> {
    const model = options?.model ?? "text-embedding-3-small";

    const response = await this.client.embeddings.create({
      model,
      input: text,
    });

    return {
      embedding: response.data[0].embedding,
      model,
      provider: "openai" as ModelProvider,
    };
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.models.list();
      return response.data.length > 0;
    } catch {
      return false;
    }
  }

  getModelName(): string {
    return this.defaultModel;
  }

  getProviderName(): string {
    return "openai";
  }
}
