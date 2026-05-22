import { z } from "zod";

export const AgentTypeSchema = z.enum(["coding", "lore", "research", "image", "audio"]);
export type AgentType = z.infer<typeof AgentTypeSchema>;

export const AgentPermissionSchema = z.enum([
  "read_memory",
  "write_memory",
  "read_lore",
  "write_lore",
  "web_search",
  "image_generation",
  "tts_control",
  "audio_control",
  "ambient_control",
  "file_read",
  "file_write",
  "code_execution",
  "shell_command",
]);
export type AgentPermission = z.infer<typeof AgentPermissionSchema>;

export const ToolDefinitionSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.record(z.unknown()),
  required_permissions: z.array(AgentPermissionSchema),
});
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

export const AgentConfigSchema = z.object({
  id: z.string(),
  type: AgentTypeSchema,
  name: z.string(),
  description: z.string(),
  permissions: z.array(AgentPermissionSchema),
  tools: z.array(ToolDefinitionSchema).default([]),
  max_tokens: z.number().default(4096),
  temperature: z.number().min(0).max(2).default(0.7),
  system_prompt: z.string(),
  fallback_message: z.string().default("I am unable to process that request right now."),
});
export type AgentConfig = z.infer<typeof AgentConfigSchema>;

export const AgentResultSchema = z.object({
  success: z.boolean(),
  content: z.string(),
  metadata: z.record(z.unknown()).default({}),
  error: z.string().nullable(),
  agent_type: AgentTypeSchema,
  latency_ms: z.number().optional(),
});
export type AgentResult = z.infer<typeof AgentResultSchema>;

export const AgentInputSchema = z.object({
  text: z.string(),
  context: z.record(z.unknown()).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});
export type AgentInput = z.infer<typeof AgentInputSchema>;
