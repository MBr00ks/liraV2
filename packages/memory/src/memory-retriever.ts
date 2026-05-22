import { MemoryRetrievalRequest, MemoryRecord, VectorSearchResult, MemoryCategory } from "./types";
import { PostgresClient } from "./postgres-client";
import { QdrantClient } from "./qdrant-client";
import { get_logger } from "./logging";

const logger = get_logger("memory-retriever");

interface RetrievalScoredResult {
  record: MemoryRecord;
  vectorScore: number;
  keywordScore: number;
  importanceWeight: number;
  finalScore: number;
}

export class MemoryRetriever {
  private postgres: PostgresClient;
  private qdrant: QdrantClient;
  private embedFn: (text: string) => Promise<number[]>;

  constructor(postgres: PostgresClient, qdrant: QdrantClient, embedFn: (text: string) => Promise<number[]>) {
    this.postgres = postgres;
    this.qdrant = qdrant;
    this.embedFn = embedFn;
  }

  async retrieve(request: MemoryRetrievalRequest): Promise<MemoryRecord[]> {
    const { query, categories, limit, min_importance, include_embeddings } = request;

    const vectorResults = include_embeddings ? await this.vectorSearch(query, categories, limit * 2) : [];
    const keywordResults = await this.keywordSearch(query, categories, limit * 2);

    const merged = this.mergeAndScore(vectorResults, keywordResults, min_importance);
    const sorted = merged.sort((a, b) => b.finalScore - a.finalScore);

    return sorted.slice(0, limit).map((r) => r.record);
  }

  async retrieveByCategory(category: MemoryCategory, limit: number = 10): Promise<MemoryRecord[]> {
    return this.postgres.getByCategory(category, limit);
  }

  async retrieveRecent(limit: number = 20): Promise<MemoryRecord[]> {
    return this.postgres.getRecentAcrossCategories(limit);
  }

  async retrieveImportant(limit: number = 10): Promise<MemoryRecord[]> {
    const allCategories: MemoryCategory[] = ["identity", "relationship", "lore", "project", "episodic", "technical"];
    const results: MemoryRecord[] = [];

    for (const category of allCategories) {
      const records = await this.postgres.getByCategory(category, limit);
      results.push(...records.filter((r) => r.importance >= 4));
    }

    return results.sort((a, b) => b.importance - a.importance).slice(0, limit);
  }

  private async vectorSearch(
    query: string,
    categories?: MemoryCategory[],
    limit: number = 20,
  ): Promise<VectorSearchResult[]> {
    try {
      const embedding = await this.embedFn(query);
      return this.qdrant.search(embedding, limit, categories);
    } catch (error) {
      logger.error("Vector search failed, falling back to keyword", { error: String(error) });
      return [];
    }
  }

  private async keywordSearch(
    query: string,
    categories?: MemoryCategory[],
    limit: number = 20,
  ): Promise<MemoryRecord[]> {
    const targets = categories ?? ["identity", "relationship", "lore", "project", "episodic", "technical"];
    const results: MemoryRecord[] = [];

    for (const category of targets) {
      const matches = await this.postgres.searchByTitle(category, query, Math.ceil(limit / targets.length));
      results.push(...matches);
    }

    return results;
  }

  private mergeAndScore(
    vectorResults: VectorSearchResult[],
    keywordResults: MemoryRecord[],
    minImportance: number,
  ): RetrievalScoredResult[] {
    const recordMap = new Map<number, RetrievalScoredResult>();

    for (const vr of vectorResults) {
      const memoryId = Number(vr.payload.memory_id);
      if (isNaN(memoryId)) continue;

      const record: MemoryRecord = {
        id: memoryId,
        category: (vr.payload.category as MemoryCategory) ?? "episodic",
        title: String(vr.payload.title ?? ""),
        content: String(vr.payload.content ?? ""),
        importance: Number(vr.payload.importance ?? 3),
        metadata: (vr.payload.metadata as Record<string, unknown>) ?? {},
        created_at: String(vr.payload.created_at ?? ""),
        updated_at: String(vr.payload.updated_at ?? ""),
        last_accessed_at: (vr.payload.last_accessed_at as string | null) ?? null,
        access_count: Number(vr.payload.access_count ?? 0),
      };

      if (record.importance < minImportance) continue;

      recordMap.set(memoryId, {
        record,
        vectorScore: vr.score,
        keywordScore: 0,
        importanceWeight: record.importance / 5,
        finalScore: 0,
      });
    }

    for (const kr of keywordResults) {
      if (kr.importance < minImportance) continue;

      const existing = recordMap.get(kr.id);
      if (existing) {
        existing.keywordScore = 0.8;
        existing.finalScore = this.calculateFinalScore(existing);
      } else {
        const entry: RetrievalScoredResult = {
          record: kr,
          vectorScore: 0,
          keywordScore: 0.8,
          importanceWeight: kr.importance / 5,
          finalScore: 0,
        };
        entry.finalScore = this.calculateFinalScore(entry);
        recordMap.set(kr.id, entry);
      }
    }

    for (const [, entry] of recordMap) {
      entry.finalScore = this.calculateFinalScore(entry);
    }

    return Array.from(recordMap.values());
  }

  private calculateFinalScore(result: RetrievalScoredResult): number {
    const vectorWeight = 0.4;
    const keywordWeight = 0.3;
    const importanceWeight = 0.3;

    return (
      result.vectorScore * vectorWeight +
      result.keywordScore * keywordWeight +
      result.importanceWeight * importanceWeight
    );
  }
}
