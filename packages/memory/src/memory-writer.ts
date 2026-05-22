import { MemoryCategory, MemoryWritePayload, MemoryWriteResult, MemoryRecord } from "./types";
import { PostgresClient } from "./postgres-client";
import { QdrantClient } from "./qdrant-client";
import { get_logger } from "./logging";

const logger = get_logger("memory-writer");

interface DuplicateCheckResult {
  isDuplicate: boolean;
  existingId: number | null;
  similarity: number;
}

export class MemoryWriter {
  private postgres: PostgresClient;
  private qdrant: QdrantClient;
  private embedFn: (text: string) => Promise<number[]>;

  constructor(postgres: PostgresClient, qdrant: QdrantClient, embedFn: (text: string) => Promise<number[]>) {
    this.postgres = postgres;
    this.qdrant = qdrant;
    this.embedFn = embedFn;
  }

  async write(category: MemoryCategory, payload: MemoryWritePayload): Promise<MemoryWriteResult> {
    const duplicateCheck = await this.checkDuplicate(category, payload);

    if (duplicateCheck.isDuplicate && payload.merge_strategy === "ignore") {
      logger.info("Duplicate memory ignored", { category, title: payload.title });
      return {
        id: duplicateCheck.existingId ?? 0,
        created: false,
        merged: false,
        category,
        importance: payload.importance,
      };
    }

    if (duplicateCheck.isDuplicate && payload.merge_strategy === "update_existing") {
      const updated = await this.postgres.update(category, duplicateCheck.existingId!, {
        content: payload.content,
        importance: Math.max(payload.importance, duplicateCheck.similarity > 0.9 ? payload.importance + 1 : payload.importance),
        metadata: payload.metadata,
      });

      if (updated) {
        await this.updateVector(duplicateCheck.existingId!, category, payload);
        logger.info("Memory updated (merge)", { category, id: duplicateCheck.existingId });
      }

      return {
        id: duplicateCheck.existingId!,
        created: false,
        merged: true,
        category,
        importance: payload.importance,
      };
    }

    const id = await this.postgres.insert(category, payload);

    await this.storeVector(id, category, payload);

    logger.info("Memory created", { category, id, title: payload.title });

    return {
      id,
      created: true,
      merged: false,
      category,
      importance: payload.importance,
    };
  }

  async writeBatch(entries: Array<{ category: MemoryCategory; payload: MemoryWritePayload }>): Promise<MemoryWriteResult[]> {
    const results: MemoryWriteResult[] = [];

    for (const entry of entries) {
      const result = await this.write(entry.category, entry.payload);
      results.push(result);
    }

    return results;
  }

  async delete(category: MemoryCategory, id: number): Promise<boolean> {
    const deleted = await this.postgres.delete(category, id);

    if (deleted) {
      await this.qdrant.delete(`memory_${id}`);
      logger.info("Memory deleted (both stores)", { category, id });
    }

    return deleted;
  }

  private async checkDuplicate(category: MemoryCategory, payload: MemoryWritePayload): Promise<DuplicateCheckResult> {
    const existing = await this.postgres.searchByTitle(category, payload.title, 5);

    if (existing.length === 0) {
      return { isDuplicate: false, existingId: null, similarity: 0 };
    }

    try {
      const newEmbedding = await this.embedFn(payload.content);
      let bestMatch: { id: number; similarity: number } = { id: 0, similarity: 0 };

      for (const record of existing) {
        const existingEmbedding = await this.embedFn(record.content);
        const similarity = this.cosineSimilarity(newEmbedding, existingEmbedding);

        if (similarity > bestMatch.similarity) {
          bestMatch = { id: record.id, similarity };
        }
      }

      if (bestMatch.similarity > 0.85) {
        return { isDuplicate: true, existingId: bestMatch.id, similarity: bestMatch.similarity };
      }
    } catch (error) {
      logger.warn("Duplicate check failed, proceeding with create", { error: String(error) });
    }

    return { isDuplicate: false, existingId: null, similarity: 0 };
  }

  private async storeVector(id: number, category: MemoryCategory, payload: MemoryWritePayload): Promise<void> {
    try {
      const embedding = await this.embedFn(payload.content);
      const vectorId = `memory_${id}`;

      await this.qdrant.upsert(vectorId, embedding, {
        memory_id: id,
        category,
        title: payload.title,
        content: payload.content,
        importance: payload.importance,
        metadata: payload.metadata,
        created_at: new Date().toISOString(),
      });
    } catch (error) {
      logger.error("Failed to store vector", { id, error: String(error) });
    }
  }

  private async updateVector(id: number, category: MemoryCategory, payload: MemoryWritePayload): Promise<void> {
    try {
      const embedding = await this.embedFn(payload.content);
      const vectorId = `memory_${id}`;

      await this.qdrant.upsert(vectorId, embedding, {
        memory_id: id,
        category,
        title: payload.title,
        content: payload.content,
        importance: payload.importance,
        metadata: payload.metadata,
        updated_at: new Date().toISOString(),
      });
    } catch (error) {
      logger.error("Failed to update vector", { id, error: String(error) });
    }
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    if (normA === 0 || normB === 0) return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }
}
