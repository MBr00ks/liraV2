import { z } from "zod";

// Memory categories
export const MemoryCategorySchema = z.enum([
  "identity",
  "relationship",
  "lore",
  "project",
  "episodic",
  "technical",
]);

export type MemoryCategory = z.infer<typeof MemoryCategorySchema>;

// Merge strategies
export const MergeStrategySchema = z.enum([
  "create_new",
  "update_existing",
  "ignore",
]);

export type MergeStrategy = z.infer<typeof MergeStrategySchema>;

// Memory record
export const MemorySchema = z.object({
  id: z.number(),
  category: MemoryCategorySchema,
  title: z.string(),
  content: z.string(),
  importance: z.number().min(1).max(5),
  metadata: z.record(z.unknown()).default({}),
  created_at: z.string(),
  updated_at: z.string(),
  last_accessed_at: z.string().nullable(),
  access_count: z.number().default(0),
});

export type Memory = z.infer<typeof MemorySchema>;

// Memory write result
export const MemoryWriteResultSchema = z.object({
  should_save: z.boolean(),
  category: MemoryCategorySchema.optional(),
  title: z.string().optional(),
  content: z.string().optional(),
  importance: z.number().min(1).max(5).optional(),
  merge_strategy: MergeStrategySchema.optional(),
});

export type MemoryWriteResult = z.infer<typeof MemoryWriteResultSchema>;

// Conversation message
export const MessageSchema = z.object({
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
});

export type Message = z.infer<typeof MessageSchema>;

// Chat request
export const ChatRequestSchema = z.object({
  message: z.string(),
  sessionId: z.string().optional(),
  stream: z.boolean().default(true),
  mode: z.string().optional(),
});

export type ChatRequest = z.infer<typeof ChatRequestSchema>;

// Personality modes
export const PersonalityModeSchema = z.enum([
  "work",
  "between",
  "narrator",
  "romantic",
  "public_safe",
  "creative_frenzy",
]);

export type PersonalityMode = z.infer<typeof PersonalityModeSchema>;

// Emotion state
export const EmotionStateSchema = z.object({
  mood: z.string().nullable(),
  relationship_level: z.number().min(0).max(10).default(0),
  personality_mode: PersonalityModeSchema.default("work"),
  last_interaction: z.string(),
  unresolved_topics: z.array(z.string()).default([]),
  metadata: z.record(z.unknown()).default({}),
});

export type EmotionState = z.infer<typeof EmotionStateSchema>;

// Intent types
export const IntentSchema = z.enum([
  "coding",
  "emotional_support",
  "lore_discussion",
  "story_narration",
  "technical_troubleshooting",
  "romantic_interaction",
  "realtime_interruption",
  "visual_request",
  "image_generation",
  "video_generation",
]);

export type Intent = z.infer<typeof IntentSchema>;

// API response envelope
export const ApiResponseSchema = z.object({
  status: z.enum(["ok", "error"]),
  data: z.unknown().nullable(),
  error: z.string().nullable(),
  request_id: z.string().uuid(),
  latency_ms: z.number().optional(),
});

export type ApiResponse = z.infer<typeof ApiResponseSchema>;
