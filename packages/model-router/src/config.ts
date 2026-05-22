import { ModelProvider, ModelRole, RouteConfig, RouteConfigSchema } from "./types";

export const defaultRoutingConfig: Map<ModelRole, RouteConfig> = new Map([
  [
    "chat",
    RouteConfigSchema.parse({
      role: "chat",
      provider: "ollama",
      model: "qwen3:32b",
      fallback_model: "gpt-4.1",
      max_tokens: 4096,
      temperature: 0.7,
      top_p: 1.0,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 30000,
    }),
  ],
  [
    "code",
    RouteConfigSchema.parse({
      role: "code",
      provider: "ollama",
      model: "devstral:latest",
      fallback_model: "gpt-4.1",
      max_tokens: 8192,
      temperature: 0.2,
      top_p: 0.9,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 60000,
    }),
  ],
  [
    "narrative",
    RouteConfigSchema.parse({
      role: "narrative",
      provider: "ollama",
      model: "magnum:latest",
      fallback_model: "gpt-4.1",
      max_tokens: 4096,
      temperature: 0.9,
      top_p: 1.0,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 45000,
    }),
  ],
  [
    "reasoning",
    RouteConfigSchema.parse({
      role: "reasoning",
      provider: "ollama",
      model: "deepseek-r1:latest",
      fallback_model: "gpt-4.1",
      max_tokens: 8192,
      temperature: 0.6,
      top_p: 0.95,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 90000,
    }),
  ],
  [
    "embedding",
    RouteConfigSchema.parse({
      role: "embedding",
      provider: "ollama",
      model: process.env.OLLAMA_EMBEDDING_MODEL ?? "nomic-embed-text",
      fallback_model: "text-embedding-3-small",
      max_tokens: 8192,
      temperature: 0,
      top_p: 1.0,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 15000,
    }),
  ],
  [
    "vision",
    RouteConfigSchema.parse({
      role: "vision",
      provider: "ollama",
      model: "llava:latest",
      fallback_model: "gpt-4.1",
      max_tokens: 4096,
      temperature: 0.5,
      top_p: 0.9,
      base_url: process.env.OLLAMA_BASE_URL,
      api_key_env: "OPENAI_API_KEY",
      timeout_ms: 30000,
    }),
  ],
]);

export function resolveRouteConfig(route: RouteConfig): RouteConfig {
  const validated = RouteConfigSchema.parse(route);

  if (validated.provider === "openai" && !process.env.OPENAI_API_KEY) {
    throw new Error("OpenAI provider requires OPENAI_API_KEY environment variable");
  }

  return validated;
}

export function getRouteForIntent(intent: string): ModelRole {
  const intentToRole: Record<string, ModelRole> = {
    coding: "code",
    emotional_support: "chat",
    lore_discussion: "narrative",
    story_narration: "narrative",
    technical_troubleshooting: "chat",
    romantic_interaction: "chat",
    realtime_interruption: "chat",
    visual_request: "vision",
    image_generation: "vision",
    video_generation: "vision",
    reasoning: "reasoning",
    analysis: "reasoning",
  };

  return intentToRole[intent] ?? "chat";
}
