import { z } from "zod";
import { MemoryCategorySchema, MergeStrategySchema } from "@lira/shared-types";

export const MemoryCategory = MemoryCategorySchema;
export type MemoryCategory = z.infer<typeof MemoryCategorySchema>;

export const MergeStrategy = MergeStrategySchema;
export type MergeStrategy = z.infer<typeof MergeStrategySchema>;

export const MemoryRecordSchema = z.object({
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
  embedding_id: z.string().nullable().optional(),
});
export type MemoryRecord = z.infer<typeof MemoryRecordSchema>;

export const MemoryWritePayloadSchema = z.object({
  category: MemoryCategorySchema,
  title: z.string(),
  content: z.string(),
  importance: z.number().min(1).max(5).default(3),
  metadata: z.record(z.unknown()).default({}),
  merge_strategy: MergeStrategySchema.default("create_new"),
});
export type MemoryWritePayload = z.infer<typeof MemoryWritePayloadSchema>;

export const MemoryQueryResultSchema = z.object({
  records: z.array(MemoryRecordSchema),
  total: z.number(),
  category: MemoryCategorySchema.optional(),
});
export type MemoryQueryResult = z.infer<typeof MemoryQueryResultSchema>;

export const VectorSearchResultSchema = z.object({
  id: z.string(),
  score: z.number(),
  payload: z.record(z.unknown()),
  category: MemoryCategorySchema.optional(),
});
export type VectorSearchResult = z.infer<typeof VectorSearchResultSchema>;

export const MemoryRetrievalRequestSchema = z.object({
  query: z.string(),
  categories: z.array(MemoryCategorySchema).optional(),
  limit: z.number().default(10),
  min_importance: z.number().default(1),
  include_embeddings: z.boolean().default(true),
});
export type MemoryRetrievalRequest = z.infer<typeof MemoryRetrievalRequestSchema>;

export const MemoryWriteResultSchema = z.object({
  id: z.number(),
  created: z.boolean(),
  merged: z.boolean(),
  category: MemoryCategorySchema,
  importance: z.number(),
});
export type MemoryWriteResult = z.infer<typeof MemoryWriteResultSchema>;

export const ImportanceScoreSchema = z.object({
  base: z.number().min(1).max(5),
  emotional: z.number().min(0).max(3).default(0),
  recurrence: z.number().min(0).max(2).default(0),
  recency: z.number().min(0).max(1).default(0),
  total: z.number().min(1).max(5),
});
export type ImportanceScore = z.infer<typeof ImportanceScoreSchema>;
