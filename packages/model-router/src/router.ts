import { Intent, PersonalityMode } from "@lira/shared-types";
import { ModelProvider, ModelRole, RouteConfig, ChatMessage, ChatResponse, StreamChunk, EmbeddingResponse } from "./types";
import { LLMAdapterInterface, ChatOptions } from "./adapter";
import { OllamaClient } from "./ollama-client";
import { OpenAIClient } from "./openai-client";
import { defaultRoutingConfig, resolveRouteConfig } from "./config";
import { get_logger } from "./logging";

const logger = get_logger("model-router");

export class ModelRouter {
  private clients: Map<ModelProvider, LLMAdapterInterface>;
  private routes: Map<ModelRole, RouteConfig>;

  constructor(customRoutes?: Map<ModelRole, RouteConfig>) {
    this.routes = customRoutes ?? defaultRoutingConfig;
    this.clients = new Map();
    this.initializeClients();
  }

  private initializeClients(): void {
    const uniqueProviders = new Set<ModelProvider>();

    for (const [, route] of this.routes) {
      uniqueProviders.add(route.provider);
    }

    for (const provider of uniqueProviders) {
      try {
        const client = this.createClient(provider);
        this.clients.set(provider, client);
      } catch (error) {
        logger.error("Failed to initialize provider", { provider, error: String(error) });
      }
    }
  }

  private createClient(provider: ModelProvider): LLMAdapterInterface {
    switch (provider) {
      case "ollama": {
        const baseUrl = process.env.OLLAMA_BASE_URL ?? "http://localhost:11434";
        return new OllamaClient(baseUrl);
      }
      case "openai": {
        const apiKey = process.env.OPENAI_API_KEY ?? "";
        const baseUrl = process.env.OPENAI_BASE_URL;
        return new OpenAIClient(apiKey, baseUrl);
      }
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  }

  async routeChat(
    intent: Intent,
    messages: ChatMessage[],
    mode?: PersonalityMode,
    options?: ChatOptions,
  ): Promise<ChatResponse> {
    const role = this.intentToRole(intent);
    const route = this.routes.get(role);

    if (!route) {
      throw new Error(`No route configured for role: ${role}`);
    }

    const enrichedMessages = this.enrichMessages(messages, mode);
    const client = this.getClient(route.provider);

    try {
      const response = await client.chat(enrichedMessages, {
        temperature: route.temperature,
        max_tokens: route.max_tokens,
        top_p: route.top_p,
        ...options,
      });

      return response;
    } catch (error) {
      if (route.fallback_model) {
        logger.warn("Primary model failed, using fallback", {
          primary: route.model,
          fallback: route.fallback_model,
        });
        return this.retryWithFallback(route, enrichedMessages, options);
      }
      throw error;
    }
  }

  async *routeStreamChat(
    intent: Intent,
    messages: ChatMessage[],
    mode?: PersonalityMode,
    options?: ChatOptions,
  ): AsyncGenerator<StreamChunk, void, unknown> {
    const role = this.intentToRole(intent);
    const route = this.routes.get(role);

    if (!route) {
      throw new Error(`No route configured for role: ${role}`);
    }

    const enrichedMessages = this.enrichMessages(messages, mode);
    const client = this.getClient(route.provider);

    yield* client.streamChat(enrichedMessages, {
      temperature: route.temperature,
      max_tokens: route.max_tokens,
      top_p: route.top_p,
      stream: true,
      ...options,
    });
  }

  async routeEmbed(text: string, options?: { model?: string }): Promise<EmbeddingResponse> {
    const embeddingRoute = this.routes.get("embedding");

    if (!embeddingRoute) {
      throw new Error("No embedding route configured");
    }

    const client = this.getClient(embeddingRoute.provider);
    return client.embed(text, options);
  }

  private intentToRole(intent: Intent): ModelRole {
    const mapping: Record<Intent, ModelRole> = {
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
    };

    return mapping[intent] ?? "chat";
  }

  private enrichMessages(messages: ChatMessage[], mode?: PersonalityMode): ChatMessage[] {
    if (!mode) return messages;

    const modeInstructions: Record<PersonalityMode, string> = {
      work: "Respond with focused, technical precision. Be supportive and precise.",
      between: "Respond with mystery and emotional depth. The Between is your native domain.",
      narrator: "Respond cinematically. Paint vivid scenes with descriptive language.",
      romantic: "Respond with warmth, intimacy, and emotional vulnerability.",
      public_safe: "Keep responses appropriate for public settings. Avoid intimate or romantic content.",
      creative_frenzy: "Respond with high energy and abundant ideas. Be highly collaborative.",
    };

    const systemMessage = messages.find((m) => m.role === "system");
    if (systemMessage) {
      return messages.map((m) =>
        m.role === "system"
          ? { ...m, content: `${m.content}\n\n[Current mode: ${mode}] ${modeInstructions[mode]}` }
          : m,
      );
    }

    return [
      { role: "system", content: `[Current mode: ${mode}] ${modeInstructions[mode]}` },
      ...messages,
    ];
  }

  private getClient(provider: ModelProvider): LLMAdapterInterface {
    const client = this.clients.get(provider);
    if (!client) {
      throw new Error(`Client not initialized for provider: ${provider}`);
    }
    return client;
  }

  private async retryWithFallback(
    route: RouteConfig,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<ChatResponse> {
    if (!route.fallback_model) {
      throw new Error(`No fallback model configured for ${route.model}`);
    }

    const fallbackRoute: RouteConfig = {
      ...route,
      model: route.fallback_model,
      fallback_model: undefined,
    };

    const resolvedConfig = resolveRouteConfig(fallbackRoute);
    const client = this.getClient(resolvedConfig.provider);
    return client.chat(messages, options);
  }

  getRouteForRole(role: ModelRole): RouteConfig | undefined {
    return this.routes.get(role);
  }

  getAllRoutes(): Map<ModelRole, RouteConfig> {
    return new Map(this.routes);
  }

  async healthCheck(): Promise<Map<ModelProvider, boolean>> {
    const results = new Map<ModelProvider, boolean>();

    for (const [provider, client] of this.clients) {
      try {
        const healthy = await client.healthCheck();
        results.set(provider, healthy);
      } catch {
        results.set(provider, false);
      }
    }

    return results;
  }
}
