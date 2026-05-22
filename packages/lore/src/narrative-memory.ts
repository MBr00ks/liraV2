import { z } from "zod";
import { MemoryWriter, MemoryRetriever, MemoryPrioritizer } from "@lira/memory";
import { get_logger } from "./logging";

const logger = get_logger("narrative-memory");

const NarrativeSceneSchema = z.object({
  id: z.string(),
  title: z.string(),
  content: z.string(),
  characters: z.array(z.string()).default([]),
  locations: z.array(z.string()).default([]),
  emotions: z.array(z.string()).default([]),
  themes: z.array(z.string()).default([]),
  timestamp: z.string(),
  importance: z.number().min(1).max(5).default(3),
  is_canon: z.boolean().default(false),
  metadata: z.record(z.unknown()).default({}),
});
type NarrativeScene = z.infer<typeof NarrativeSceneSchema>;

const ConsistencyEventSchema = z.object({
  id: z.string(),
  description: z.string(),
  character: z.string().optional(),
  location: z.string().optional(),
  timestamp: z.string(),
  previous_state: z.string().optional(),
  new_state: z.string(),
  potential_conflicts: z.array(z.string()).default([]),
});
type ConsistencyEvent = z.infer<typeof ConsistencyEventSchema>;

export class NarrativeMemory {
  private memoryWriter: MemoryWriter;
  private memoryRetriever: MemoryRetriever;
  private memoryPrioritizer: MemoryPrioritizer;
  private sceneIndex: Map<string, NarrativeScene> = new Map();
  private consistencyLog: ConsistencyEvent[] = [];

  constructor(memoryWriter: MemoryWriter, memoryRetriever: MemoryRetriever, memoryPrioritizer: MemoryPrioritizer) {
    this.memoryWriter = memoryWriter;
    this.memoryRetriever = memoryRetriever;
    this.memoryPrioritizer = memoryPrioritizer;
  }

  async store(sceneInput: Omit<NarrativeScene, "id">): Promise<string> {
    const scene: NarrativeScene = {
      ...sceneInput,
      id: generateId("scene"),
    };

    this.sceneIndex.set(scene.id, scene);

    try {
      await this.memoryWriter.write("lore", {
        category: "lore",
        title: scene.title,
        content: scene.content,
        importance: scene.importance,
        metadata: {
          scene_id: scene.id,
          characters: scene.characters,
          locations: scene.locations,
          emotions: scene.emotions,
          themes: scene.themes,
          is_canon: scene.is_canon,
          ...scene.metadata,
        },
        merge_strategy: "create_new",
      });

      logger.info("Narrative scene stored", { sceneId: scene.id, title: scene.title });
      return scene.id;
    } catch (error) {
      logger.error("Failed to store narrative scene", { sceneId: scene.id, error: String(error) });
      return scene.id;
    }
  }

  async recall(query: string, limit: number = 10): Promise<NarrativeScene[]> {
    const localMatches = this.searchLocalScenes(query);

    try {
      const memoryResults = await this.memoryRetriever.retrieve({
        query,
        categories: ["lore"],
        limit,
        min_importance: 1,
        include_embeddings: true,
      });

      const memoryScenes: NarrativeScene[] = memoryResults
        .map((record) => {
          const meta = record.metadata as Record<string, unknown>;
          return {
            id: `scene_${record.id}`,
            title: record.title,
            content: record.content,
            characters: (meta.characters as string[]) ?? [],
            locations: (meta.locations as string[]) ?? [],
            emotions: (meta.emotions as string[]) ?? [],
            themes: (meta.themes as string[]) ?? [],
            timestamp: record.created_at,
            importance: record.importance,
            is_canon: (meta.is_canon as boolean) ?? false,
            metadata: meta,
          };
        })
        .filter((s) => !this.sceneIndex.has(s.id));

      const combined = [...localMatches, ...memoryScenes];
      const sorted = combined.sort((a, b) => b.importance - a.importance);

      logger.info("Narrative recall completed", { query, resultCount: sorted.length });
      return sorted.slice(0, limit);
    } catch (error) {
      logger.error("Narrative recall failed", { query, error: String(error) });
      return localMatches.slice(0, limit);
    }
  }

  async updateConsistency(eventInput: Omit<ConsistencyEvent, "id">): Promise<ConsistencyEvent> {
    const event: ConsistencyEvent = {
      ...eventInput,
      id: generateId("consistency"),
    };

    this.consistencyLog.push(event);

    if (event.potential_conflicts.length > 0) {
      logger.warn("Consistency conflict detected", {
        eventId: event.id,
        conflicts: event.potential_conflicts,
      });

      await this.flagConflicts(event);
    }

    logger.info("Consistency event logged", { eventId: event.id });
    return event;
  }

  getScene(sceneId: string): NarrativeScene | undefined {
    return this.sceneIndex.get(sceneId);
  }

  getScenesByCharacter(characterId: string): NarrativeScene[] {
    return Array.from(this.sceneIndex.values()).filter(
      (s) => s.characters.includes(characterId),
    );
  }

  getScenesByLocation(locationId: string): NarrativeScene[] {
    return Array.from(this.sceneIndex.values()).filter(
      (s) => s.locations.includes(locationId),
    );
  }

  getConsistencyLog(): ConsistencyEvent[] {
    return [...this.consistencyLog];
  }

  getConflicts(): ConsistencyEvent[] {
    return this.consistencyLog.filter(
      (e) => e.potential_conflicts.length > 0,
    );
  }

  getCanonScenes(): NarrativeScene[] {
    return Array.from(this.sceneIndex.values()).filter(
      (s) => s.is_canon,
    );
  }

  private searchLocalScenes(query: string): NarrativeScene[] {
    const normalizedQuery = query.toLowerCase();
    const terms = normalizedQuery.split(/\s+/).filter((t) => t.length > 2);

    return Array.from(this.sceneIndex.values())
      .map((scene) => {
        const content = scene.content.toLowerCase();
        const title = scene.title.toLowerCase();
        let score = 0;

        for (const term of terms) {
          if (title.includes(term)) score += 5;
          if (content.includes(term)) score += 1;
          if (scene.characters.some((c) => c.toLowerCase().includes(term))) score += 3;
          if (scene.emotions.some((e) => e.toLowerCase().includes(term))) score += 2;
          if (scene.themes.some((t) => t.toLowerCase().includes(term))) score += 2;
        }

        return { scene, score };
      })
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ scene }) => scene);
  }

  private async flagConflicts(event: ConsistencyEvent): Promise<void> {
    try {
      await this.memoryWriter.write("lore", {
        category: "lore",
        title: `Consistency conflict: ${event.description.slice(0, 50)}`,
        content: `Potential conflicts detected: ${event.potential_conflicts.join(", ")}. Event: ${event.description}`,
        importance: 4,
        metadata: {
          type: "consistency_conflict",
          event_id: event.id,
          conflicts: event.potential_conflicts,
        },
        merge_strategy: "create_new",
      });
    } catch (error) {
      logger.error("Failed to flag consistency conflict", { error: String(error) });
    }
  }
}

function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
