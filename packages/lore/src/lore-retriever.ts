import { z } from "zod";
import { LoreEntry, LoreEntrySchema } from "./types";
import { MemoryRetriever } from "@lira/memory";
import { get_logger } from "./logging";

const logger = get_logger("lore-retriever");

const LoreSearchResultSchema = z.object({
  entries: z.array(LoreEntrySchema),
  total: z.number(),
  query: z.string(),
});
type LoreSearchResult = z.infer<typeof LoreSearchResultSchema>;

export class LoreRetriever {
  private memoryRetriever: MemoryRetriever;
  private localIndex: Map<string, LoreEntry> = new Map();

  constructor(memoryRetriever: MemoryRetriever) {
    this.memoryRetriever = memoryRetriever;
  }

  async search(query: string, limit: number = 10): Promise<LoreSearchResult> {
    try {
      const memoryResults = await this.memoryRetriever.retrieve({
        query,
        categories: ["lore"],
        limit,
        min_importance: 1,
        include_embeddings: true,
      });

      const entries: LoreEntry[] = memoryResults.map((record, index) => ({
        id: `lore_${record.id}`,
        title: record.title,
        content: record.content,
        category: "concept",
        tags: [],
        created_at: record.created_at,
        updated_at: record.updated_at,
        canon_verified: record.importance >= 4,
        importance: record.importance,
        metadata: record.metadata as Record<string, unknown>,
      }));

      const localMatches = this.searchLocalIndex(query);
      entries.push(...localMatches);

      const result: LoreSearchResult = {
        entries,
        total: entries.length,
        query,
      };

      logger.info("Lore search completed", { query, resultCount: entries.length });
      return result;
    } catch (error) {
      logger.error("Lore search failed", { query, error: String(error) });

      const localOnly = this.searchLocalIndex(query);
      return {
        entries: localOnly,
        total: localOnly.length,
        query,
      };
    }
  }

  async getByCategory(category: LoreEntry["category"], limit: number = 20): Promise<LoreEntry[]> {
    try {
      const memoryResults = await this.memoryRetriever.retrieveByCategory("lore", limit);

      const entries: LoreEntry[] = memoryResults.map((record) => ({
        id: `lore_${record.id}`,
        title: record.title,
        content: record.content,
        category,
        tags: [],
        created_at: record.created_at,
        updated_at: record.updated_at,
        canon_verified: record.importance >= 4,
        importance: record.importance,
        metadata: record.metadata as Record<string, unknown>,
      }));

      const localFiltered = Array.from(this.localIndex.values()).filter(
        (e) => e.category === category,
      );
      entries.push(...localFiltered);

      logger.info("Category retrieval completed", { category, resultCount: entries.length });
      return entries;
    } catch (error) {
      logger.error("Category retrieval failed", { category, error: String(error) });

      return Array.from(this.localIndex.values()).filter(
        (e) => e.category === category,
      );
    }
  }

  async getRelated(entryId: string, limit: number = 5): Promise<LoreEntry[]> {
    const entry = this.localIndex.get(entryId);
    if (!entry) {
      logger.warn("Entry not found for related lookup", { entryId });
      return [];
    }

    try {
      const memoryResults = await this.memoryRetriever.retrieve({
        query: entry.content.slice(0, 200),
        categories: ["lore"],
        limit: limit + 1,
        min_importance: 1,
        include_embeddings: true,
      });

      const related: LoreEntry[] = memoryResults
        .filter((r) => `lore_${r.id}` !== entryId)
        .slice(0, limit)
        .map((record) => ({
          id: `lore_${record.id}`,
          title: record.title,
          content: record.content,
          category: "concept",
          tags: [],
          created_at: record.created_at,
          updated_at: record.updated_at,
          canon_verified: record.importance >= 4,
          importance: record.importance,
          metadata: record.metadata as Record<string, unknown>,
        }));

      logger.info("Related entries retrieved", { entryId, count: related.length });
      return related;
    } catch (error) {
      logger.error("Related retrieval failed", { entryId, error: String(error) });
      return [];
    }
  }

  async getUnresolvedMysteries(): Promise<LoreEntry[]> {
    try {
      const memoryResults = await this.memoryRetriever.retrieve({
        query: "unresolved mystery open question",
        categories: ["lore"],
        limit: 20,
        min_importance: 2,
        include_embeddings: true,
      });

      const unresolved: LoreEntry[] = memoryResults
        .filter((r) => {
          const meta = r.metadata as Record<string, unknown>;
          return meta.status === "unresolved" || meta.type === "mystery";
        })
        .map((record) => ({
          id: `lore_${record.id}`,
          title: record.title,
          content: record.content,
          category: "concept",
          tags: ["unresolved", "mystery"],
          created_at: record.created_at,
          updated_at: record.updated_at,
          canon_verified: false,
          importance: record.importance,
          metadata: record.metadata as Record<string, unknown>,
        }));

      logger.info("Unresolved mysteries retrieved", { count: unresolved.length });
      return unresolved;
    } catch (error) {
      logger.error("Unresolved mystery retrieval failed", { error: String(error) });
      return [];
    }
  }

  indexEntry(entry: LoreEntry): void {
    this.localIndex.set(entry.id, entry);
    logger.info("Lore entry indexed locally", { entryId: entry.id, title: entry.title });
  }

  removeEntry(entryId: string): boolean {
    const removed = this.localIndex.delete(entryId);
    if (removed) {
      logger.info("Lore entry removed from local index", { entryId });
    }
    return removed;
  }

  getEntry(entryId: string): LoreEntry | undefined {
    return this.localIndex.get(entryId);
  }

  private searchLocalIndex(query: string): LoreEntry[] {
    const normalizedQuery = query.toLowerCase();
    const terms = normalizedQuery.split(/\s+/).filter((t) => t.length > 2);

    return Array.from(this.localIndex.values())
      .map((entry) => {
        const content = entry.content.toLowerCase();
        const title = entry.title.toLowerCase();
        let score = 0;

        for (const term of terms) {
          if (title.includes(term)) score += 3;
          if (content.includes(term)) score += 1;
          if (entry.tags.some((t) => t.toLowerCase().includes(term))) score += 2;
        }

        return { entry, score };
      })
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ entry }) => entry);
  }
}
