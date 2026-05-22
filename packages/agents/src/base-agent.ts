import { z } from "zod";
import {
  AgentConfig,
  AgentPermission,
  AgentResult,
  AgentInput,
  ToolDefinition,
  AgentType,
  AgentConfigSchema,
  AgentResultSchema,
  AgentInputSchema,
} from "./types";
import { get_logger } from "./logging";

export abstract class BaseAgent {
  protected config: AgentConfig;
  protected logger: ReturnType<typeof get_logger>;
  protected lastResult: AgentResult | null = null;

  constructor(config: AgentConfig) {
    this.config = AgentConfigSchema.parse(config);
    this.logger = get_logger(`agent-${this.config.type}`);
  }

  abstract execute(input: AgentInput): Promise<AgentResult>;

  canUse(toolName: string): boolean {
    const tool = this.config.tools.find((t) => t.name === toolName);
    if (!tool) return false;

    const requiredPermissions = tool.required_permissions;
    return requiredPermissions.every((p) => this.config.permissions.includes(p));
  }

  getTools(): ToolDefinition[] {
    return this.config.tools.filter((t) => this.canUse(t.name));
  }

  getConfig(): AgentConfig {
    return { ...this.config };
  }

  getType(): AgentType {
    return this.config.type;
  }

  getResult(): AgentResult | null {
    return this.lastResult;
  }

  protected handleError(error: unknown, input: AgentInput): AgentResult {
    const message = error instanceof Error ? error.message : String(error);

    this.logger.error("Agent execution failed", {
      agentType: this.config.type,
      error: message,
      inputLength: input.text.length,
    });

    const result: AgentResult = {
      success: false,
      content: this.config.fallback_message,
      metadata: {
        error_type: error instanceof Error ? error.constructor.name : "unknown",
        error_message: message,
      },
      error: message,
      agent_type: this.config.type,
    };

    this.lastResult = result;
    return result;
  }

  protected buildResult(
    content: string,
    metadata: Record<string, unknown> = {},
    latencyMs?: number,
  ): AgentResult {
    const result: AgentResult = {
      success: true,
      content,
      metadata,
      error: null,
      agent_type: this.config.type,
      latency_ms: latencyMs,
    };

    this.lastResult = result;
    return result;
  }

  protected validateInput(input: unknown): AgentInput {
    return AgentInputSchema.parse(input);
  }

  protected logExecution(input: AgentInput): void {
    this.logger.info("Agent executing", {
      agentType: this.config.type,
      inputLength: input.text.length,
      priority: input.priority,
    });
  }
}
