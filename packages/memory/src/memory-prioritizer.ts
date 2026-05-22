import { MemoryCategory, MemoryRecord, ImportanceScore } from "./types";
import { PostgresClient } from "./postgres-client";
import { get_logger } from "./logging";

const logger = get_logger("memory-prioritizer");

const EMOTIONAL_CATEGORIES: MemoryCategory[] = ["relationship", "episodic"];
const FACTUAL_CATEGORIES: MemoryCategory[] = ["identity", "lore", "project", "technical"];

export class MemoryPrioritizer {
  private postgres: PostgresClient;

  constructor(postgres: PostgresClient) {
    this.postgres = postgres;
  }

  async prioritizeAll(): Promise<void> {
    const allCategories: MemoryCategory[] = ["identity", "relationship", "lore", "project", "episodic", "technical"];

    for (const category of allCategories) {
      await this.prioritizeCategory(category);
    }

    logger.info("Memory prioritization complete");
  }

  async prioritizeCategory(category: MemoryCategory): Promise<void> {
    const records = await this.postgres.getByCategory(category, 500);

    for (const record of records) {
      const newImportance = this.calculateImportance(record);

      if (newImportance !== record.importance) {
        await this.postgres.update(category, record.id, { importance: newImportance });
        logger.debug("Memory importance updated", {
          category,
          id: record.id,
          old: record.importance,
          new: newImportance,
        });
      }
    }
  }

  calculateImportance(record: MemoryRecord): number {
    const scores = this.scoreComponents(record);
    return Math.round(scores.total);
  }

  scoreComponents(record: MemoryRecord): ImportanceScore {
    const base = record.importance;
    const emotional = this.emotionalScore(record);
    const recurrence = this.recurrenceScore(record);
    const recency = this.recencyScore(record);

    const total = this.weightedTotal(base, emotional, recurrence, recency);

    return {
      base,
      emotional,
      recurrence,
      recency,
      total: Math.min(5, Math.max(1, Math.round(total))),
    };
  }

  private emotionalScore(record: MemoryRecord): number {
    if (!EMOTIONAL_CATEGORIES.includes(record.category)) return 0;

    const content = record.content.toLowerCase();
    const emotionalIndicators = [
      "love", "miss", "happy", "sad", "angry", "afraid", "excited",
      "worried", "proud", "hurt", "comfort", "intimate", "tender",
      "crying", "laughing", "warm", "cold", "alone", "together",
    ];

    let score = 0;
    for (const indicator of emotionalIndicators) {
      if (content.includes(indicator)) score += 0.3;
    }

    const metadata = record.metadata as Record<string, unknown>;
    if (metadata.emotion_intensity) {
      score += Number(metadata.emotion_intensity) * 0.5;
    }

    return Math.min(3, score);
  }

  private recurrenceScore(record: MemoryRecord): number {
    const accessCount = record.access_count;

    if (accessCount >= 10) return 2;
    if (accessCount >= 5) return 1.5;
    if (accessCount >= 3) return 1;
    if (accessCount >= 1) return 0.5;
    return 0;
  }

  private recencyScore(record: MemoryRecord): number {
    const updated = new Date(record.updated_at);
    const now = new Date();
    const daysSinceUpdate = (now.getTime() - updated.getTime()) / (1000 * 60 * 60 * 24);

    if (daysSinceUpdate <= 1) return 1;
    if (daysSinceUpdate <= 7) return 0.7;
    if (daysSinceUpdate <= 30) return 0.4;
    if (daysSinceUpdate <= 90) return 0.2;
    return 0;
  }

  private weightedTotal(base: number, emotional: number, recurrence: number, recency: number): number {
    const baseWeight = 0.4;
    const emotionalWeight = 0.3;
    const recurrenceWeight = 0.2;
    const recencyWeight = 0.1;

    return (
      base * baseWeight +
      emotional * emotionalWeight +
      recurrence * recurrenceWeight +
      recency * recencyWeight
    );
  }

  async fadeOldMemories(daysThreshold: number = 90, minImportance: number = 2): Promise<number[]> {
    const allCategories: MemoryCategory[] = ["identity", "relationship", "lore", "project", "episodic", "technical"];
    const fadedIds: number[] = [];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - daysThreshold);

    for (const category of allCategories) {
      if (FACTUAL_CATEGORIES.includes(category)) continue;

      const records = await this.postgres.getByCategory(category, 500);

      for (const record of records) {
        const updated = new Date(record.updated_at);
        if (updated < cutoff && record.importance <= minImportance && record.access_count === 0) {
          const newImportance = Math.max(1, record.importance - 1);
          await this.postgres.update(category, record.id, { importance: newImportance });
          fadedIds.push(record.id);
        }
      }
    }

    if (fadedIds.length > 0) {
      logger.info("Faded old memories", { count: fadedIds.length });
    }

    return fadedIds;
  }

  async reinforceRecurring(): Promise<number[]> {
    const allCategories: MemoryCategory[] = ["identity", "relationship", "lore", "project", "episodic", "technical"];
    const reinforcedIds: number[] = [];

    for (const category of allCategories) {
      const records = await this.postgres.getByCategory(category, 500);

      for (const record of records) {
        if (record.access_count >= 5 && record.importance < 5) {
          const newImportance = Math.min(5, record.importance + 1);
          await this.postgres.update(category, record.id, { importance: newImportance });
          reinforcedIds.push(record.id);
        }
      }
    }

    if (reinforcedIds.length > 0) {
      logger.info("Reinforced recurring memories", { count: reinforcedIds.length });
    }

    return reinforcedIds;
  }
}
