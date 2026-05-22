import { z } from "zod";

export const ModelProviderSchema = z.enum(["ollama", "openai", "anthropic", "local"]);
export type ModelProvider = z.infer<typeof ModelProviderSchema>;

export const ModelRoleSchema = z.enum(["chat", "code", "narrative", "reasoning", "embedding", "vision"]);
export type ModelRole = z.infer<typeof ModelRoleSchema>;

export const RouteConfigSchema = z.object({
  role: ModelRoleSchema,
  provider: ModelProviderSchema,
  model: z.string(),
  fallback_model: z.string().optional(),
  max_tokens: z.number().default(4096),
  temperature: z.number().min(0).max(2).default(0.7),
  top_p: z.number().min(0).max(1).default(1.0),
  base_url: z.string().optional(),
  api_key_env: z.string().optional(),
  timeout_ms: z.number().default(30000),
});
export type RouteConfig = z.infer<typeof RouteConfigSchema>;

export const ChatMessageSchema = z.object({
  role: z.enum(["system", "user", "assistant", "tool"]),
  content: z.string(),
  name: z.string().optional(),
  tool_calls: z.unknown().optional(),
  tool_call_id: z.string().optional(),
});
export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const ChatResponseSchema = z.object({
  content: z.string(),
  model: z.string(),
  provider: ModelProviderSchema,
  usage: z.object({
    prompt_tokens: z.number(),
    completion_tokens: z.number(),
    total_tokens: z.number(),
  }).optional(),
  finish_reason: z.string().optional(),
});
export type ChatResponse = z.infer<typeof ChatResponseSchema>;

export const StreamChunkSchema = z.object({
  content: z.string(),
  done: z.boolean(),
  model: z.string(),
  provider: ModelProviderSchema,
});
export type StreamChunk = z.infer<typeof StreamChunkSchema>;

export const EmbeddingResponseSchema = z.object({
  embedding: z.array(z.number()),
  model: z.string(),
  provider: ModelProviderSchema,
});
export type EmbeddingResponse = z.infer<typeof EmbeddingResponseSchema>;

export const LLMAdapterSchema = z.object({
  provider: ModelProviderSchema,
  base_url: z.string(),
  model: z.string(),
  api_key: z.string().optional(),
  timeout_ms: z.number().default(30000),
});
export type LLMAdapter = z.infer<typeof LLMAdapterSchema>;
