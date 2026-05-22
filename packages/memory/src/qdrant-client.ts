import { QdrantClient as QdrantSDK } from "@qdrant/js-client-rest";
import { VectorSearchResult, MemoryCategory } from "./types";
import { qdrantConfig } from "./config";
import { get_logger } from "./logging";

const logger = get_logger("qdrant-client");

const COLLECTION_NAME = "lira_memories";

export interface QdrantClient {
  upsert(id: string, vector: number[], payload: Record<string, unknown>): Promise<boolean>;
  search(vector: number[], limit?: number, categoryFilter?: MemoryCategory[]): Promise<VectorSearchResult[]>;
  delete(id: string): Promise<boolean>;
  deleteByCategory(category: MemoryCategory): Promise<boolean>;
  collectionExists(): Promise<boolean>;
  ensureCollection(vectorSize: number): Promise<void>;
  healthCheck(): Promise<boolean>;
}

export function createQdrantClient(): QdrantClient {
  const client = new QdrantSDK({
    url: qdrantConfig.url,
    apiKey: qdrantConfig.apiKey || undefined,
  });

  return {
    async upsert(id: string, vector: number[], payload: Record<string, unknown>): Promise<boolean> {
      try {
        await client.upsert(COLLECTION_NAME, {
          wait: true,
          points: [
            {
              id,
              vector,
              payload,
            },
          ],
        });
        return true;
      } catch (error) {
        logger.error("Failed to upsert vector", { id, error: String(error) });
        return false;
      }
    },

    async search(
      vector: number[],
      limit: number = 10,
      categoryFilter?: MemoryCategory[],
    ): Promise<VectorSearchResult[]> {
      try {
        const filter = categoryFilter
          ? {
              should: categoryFilter.map((cat) => ({
                key: "category",
                match: { value: cat },
              })),
            }
          : undefined;

        const results = await client.search(COLLECTION_NAME, {
          vector,
          limit,
          filter,
          with_payload: true,
        });

        return results.map((r) => ({
          id: String(r.id),
          score: r.score,
          payload: r.payload as Record<string, unknown>,
          category: (r.payload?.category as MemoryCategory) ?? undefined,
        }));
      } catch (error) {
        logger.error("Vector search failed", { error: String(error) });
        return [];
      }
    },

    async delete(id: string): Promise<boolean> {
      try {
        await client.delete(COLLECTION_NAME, {
          wait: true,
          points: [id],
        });
        return true;
      } catch (error) {
        logger.error("Failed to delete vector", { id, error: String(error) });
        return false;
      }
    },

    async deleteByCategory(category: MemoryCategory): Promise<boolean> {
      try {
        await client.delete(COLLECTION_NAME, {
          wait: true,
          filter: {
            must: [
              {
                key: "category",
                match: { value: category },
              },
            ],
          },
        });
        return true;
      } catch (error) {
        logger.error("Failed to delete vectors by category", { category, error: String(error) });
        return false;
      }
    },

    async collectionExists(): Promise<boolean> {
      try {
        const collections = await client.getCollections();
        return collections.collections.some((c) => c.name === COLLECTION_NAME);
      } catch {
        return false;
      }
    },

    async ensureCollection(vectorSize: number): Promise<void> {
      const exists = await this.collectionExists();
      if (exists) return;

      try {
        await client.createCollection(COLLECTION_NAME, {
          vectors: {
            size: vectorSize,
            distance: "Cosine",
          },
        });
        logger.info("Created Qdrant collection", { name: COLLECTION_NAME, vectorSize });
      } catch (error) {
        logger.error("Failed to create collection", { error: String(error) });
        throw error;
      }
    },

    async healthCheck(): Promise<boolean> {
      try {
        await client.getCollections();
        return true;
      } catch {
        return false;
      }
    },
  };
}
