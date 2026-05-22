import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { MemoryCategory, MemoryRecord, MemoryWritePayload, MemoryQueryResult } from "./types";
import { dbConfig } from "./config";
import { get_logger } from "./logging";

const logger = get_logger("postgres-client");

const MEMORY_TABLES: Record<MemoryCategory, string> = {
  identity: "memories_identity",
  relationship: "memories_relationship",
  lore: "memories_lore",
  project: "memories_project",
  episodic: "memories_episodic",
  technical: "memories_technical",
};

export interface PostgresClient {
  insert(category: MemoryCategory, payload: MemoryWritePayload): Promise<number>;
  getById(category: MemoryCategory, id: number): Promise<MemoryRecord | null>;
  getByCategory(category: MemoryCategory, limit?: number): Promise<MemoryRecord[]>;
  searchByTitle(category: MemoryCategory, query: string, limit?: number): Promise<MemoryRecord[]>;
  update(category: MemoryCategory, id: number, updates: Partial<MemoryWritePayload>): Promise<boolean>;
  delete(category: MemoryCategory, id: number): Promise<boolean>;
  incrementAccess(category: MemoryCategory, id: number): Promise<void>;
  getRecentAcrossCategories(limit?: number): Promise<MemoryRecord[]>;
  healthCheck(): Promise<boolean>;
}

export function createPostgresClient(): PostgresClient {
  const client = createClient(dbConfig.supabaseUrl, dbConfig.supabaseKey, {
    auth: { persistSession: false },
  });

  return {
    async insert(category: MemoryCategory, payload: MemoryWritePayload): Promise<number> {
      const table = MEMORY_TABLES[category];
      const now = new Date().toISOString();

      const record = {
        title: payload.title,
        content: payload.content,
        importance: payload.importance,
        metadata: payload.metadata,
        created_at: now,
        updated_at: now,
        last_accessed_at: null,
        access_count: 0,
      };

      const { data, error } = await client.from(table).insert(record).select("id").single();

      if (error) {
        logger.error("Failed to insert memory", { category, error: error.message });
        throw new Error(`Postgres insert failed: ${error.message}`);
      }

      logger.info("Memory inserted", { category, id: data.id });
      return data.id as number;
    },

    async getById(category: MemoryCategory, id: number): Promise<MemoryRecord | null> {
      const table = MEMORY_TABLES[category];

      const { data, error } = await client.from(table).select("*").eq("id", id).single();

      if (error) {
        if (error.code === "PGRST116") return null;
        logger.error("Failed to get memory by ID", { category, id, error: error.message });
        return null;
      }

      return data as MemoryRecord;
    },

    async getByCategory(category: MemoryCategory, limit: number = 50): Promise<MemoryRecord[]> {
      const table = MEMORY_TABLES[category];

      const { data, error } = await client
        .from(table)
        .select("*")
        .order("importance", { ascending: false })
        .limit(limit);

      if (error) {
        logger.error("Failed to query memories by category", { category, error: error.message });
        return [];
      }

      return (data ?? []) as MemoryRecord[];
    },

    async searchByTitle(category: MemoryCategory, query: string, limit: number = 10): Promise<MemoryRecord[]> {
      const table = MEMORY_TABLES[category];

      const { data, error } = await client
        .from(table)
        .select("*")
        .ilike("title", `%${query}%`)
        .order("importance", { ascending: false })
        .limit(limit);

      if (error) {
        logger.error("Failed to search memories", { category, query, error: error.message });
        return [];
      }

      return (data ?? []) as MemoryRecord[];
    },

    async update(category: MemoryCategory, id: number, updates: Partial<MemoryWritePayload>): Promise<boolean> {
      const table = MEMORY_TABLES[category];
      const updateData: Record<string, unknown> = {
        updated_at: new Date().toISOString(),
      };

      if (updates.title !== undefined) updateData.title = updates.title;
      if (updates.content !== undefined) updateData.content = updates.content;
      if (updates.importance !== undefined) updateData.importance = updates.importance;
      if (updates.metadata !== undefined) updateData.metadata = updates.metadata;

      const { error } = await client.from(table).update(updateData).eq("id", id);

      if (error) {
        logger.error("Failed to update memory", { category, id, error: error.message });
        return false;
      }

      return true;
    },

    async delete(category: MemoryCategory, id: number): Promise<boolean> {
      const table = MEMORY_TABLES[category];

      const { error } = await client.from(table).delete().eq("id", id);

      if (error) {
        logger.error("Failed to delete memory", { category, id, error: error.message });
        return false;
      }

      logger.info("Memory deleted", { category, id });
      return true;
    },

    async incrementAccess(category: MemoryCategory, id: number): Promise<void> {
      const table = MEMORY_TABLES[category];

      const { error } = await client.rpc("increment_memory_access", {
        table_name: table,
        memory_id: id,
      });

      if (error) {
        logger.warn("Failed to increment access count", { category, id, error: error.message });
      }
    },

    async getRecentAcrossCategories(limit: number = 20): Promise<MemoryRecord[]> {
      const allRecords: MemoryRecord[] = [];

      for (const [category, table] of Object.entries(MEMORY_TABLES)) {
        const { data, error } = await client
          .from(table)
          .select("*")
          .order("created_at", { ascending: false })
          .limit(Math.ceil(limit / Object.keys(MEMORY_TABLES).length));

        if (!error && data) {
          allRecords.push(...(data as MemoryRecord[]));
        }
      }

      return allRecords
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, limit);
    },

    async healthCheck(): Promise<boolean> {
      try {
        const { error } = await client.from("memories_identity").select("id").limit(1);
        return !error;
      } catch {
        return false;
      }
    },
  };
}
