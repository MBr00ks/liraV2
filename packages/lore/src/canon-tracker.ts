import { z } from "zod";
import { CanonEvent, Character, Location, Timeline, Mystery, StoryArc, CanonEventSchema, CharacterSchema, LocationSchema, TimelineSchema, MysterySchema, StoryArcSchema } from "./types";
import { get_logger } from "./logging";

const logger = get_logger("canon-tracker");

interface ConsistencyResult {
  is_consistent: boolean;
  violations: string[];
  warnings: string[];
}

export class CanonTracker {
  private events: Map<string, CanonEvent> = new Map();
  private characters: Map<string, Character> = new Map();
  private locations: Map<string, Location> = new Map();
  private timelines: Map<string, Timeline> = new Map();
  private mysteries: Map<string, Mystery> = new Map();
  private storyArcs: Map<string, StoryArc> = new Map();

  addEvent(eventInput: Omit<CanonEvent, "id">): string {
    const event = CanonEventSchema.parse({
      ...eventInput,
      id: generateId("event"),
    });

    this.events.set(event.id, event);

    for (const charId of event.character_ids) {
      const character = this.characters.get(charId);
      if (character && event.timestamp) {
        if (!character.last_appearance || event.timestamp > character.last_appearance) {
          character.last_appearance = event.timestamp;
        }
      }
    }

    const timeline = this.timelines.get(event.timeline_id);
    if (timeline) {
      if (!timeline.events.includes(event.id)) {
        timeline.events.push(event.id);
      }
    }

    logger.info("Canon event added", { eventId: event.id, title: event.title });
    return event.id;
  }

  addCharacter(characterInput: Omit<Character, "id">): string {
    const character = CharacterSchema.parse({
      ...characterInput,
      id: generateId("character"),
    });

    this.characters.set(character.id, character);
    logger.info("Character added", { characterId: character.id, name: character.name });
    return character.id;
  }

  addLocation(locationInput: Omit<Location, "id">): string {
    const location = LocationSchema.parse({
      ...locationInput,
      id: generateId("location"),
    });

    this.locations.set(location.id, location);
    logger.info("Location added", { locationId: location.id, name: location.name });
    return location.id;
  }

  addTimeline(timelineInput: Omit<Timeline, "id">): string {
    const timeline = TimelineSchema.parse({
      ...timelineInput,
      id: generateId("timeline"),
    });

    this.timelines.set(timeline.id, timeline);
    logger.info("Timeline added", { timelineId: timeline.id, name: timeline.name });
    return timeline.id;
  }

  addMystery(mysteryInput: Omit<Mystery, "id">): string {
    const mystery = MysterySchema.parse({
      ...mysteryInput,
      id: generateId("mystery"),
    });

    this.mysteries.set(mystery.id, mystery);
    logger.info("Mystery added", { mysteryId: mystery.id, title: mystery.title });
    return mystery.id;
  }

  addStoryArc(arcInput: Omit<StoryArc, "id">): string {
    const arc = StoryArcSchema.parse({
      ...arcInput,
      id: generateId("arc"),
    });

    this.storyArcs.set(arc.id, arc);
    logger.info("Story arc added", { arcId: arc.id, title: arc.title });
    return arc.id;
  }

  getEvents(characterId?: string): CanonEvent[] {
    if (!characterId) {
      return Array.from(this.events.values());
    }

    return Array.from(this.events.values()).filter(
      (e) => e.character_ids.includes(characterId),
    );
  }

  getTimeline(timelineId?: string): CanonEvent[] {
    const targetId = timelineId ?? this.getPrimaryTimelineId();
    if (!targetId) return [];

    const timeline = this.timelines.get(targetId);
    if (!timeline) return [];

    return timeline.events
      .map((id) => this.events.get(id))
      .filter((e): e is CanonEvent => e !== undefined);
  }

  getCharacter(characterId: string): Character | undefined {
    return this.characters.get(characterId);
  }

  getLocation(locationId: string): Location | undefined {
    return this.locations.get(locationId);
  }

  getMystery(mysteryId: string): Mystery | undefined {
    return this.mysteries.get(mysteryId);
  }

  resolveMystery(mysteryId: string, resolution: string): boolean {
    const mystery = this.mysteries.get(mysteryId);
    if (!mystery) {
      logger.warn("Mystery not found", { mysteryId });
      return false;
    }

    mystery.status = "resolved";
    mystery.resolution = resolution;
    mystery.resolved_at = new Date().toISOString();

    logger.info("Mystery resolved", { mysteryId, title: mystery.title });
    return true;
  }

  checkConsistency(eventInput: Partial<CanonEvent>): ConsistencyResult {
    const violations: string[] = [];
    const warnings: string[] = [];

    if (eventInput.character_ids) {
      for (const charId of eventInput.character_ids) {
        if (!this.characters.has(charId)) {
          violations.push(`Referenced character ${charId} does not exist in canon`);
        }
      }
    }

    if (eventInput.location_ids) {
      for (const locId of eventInput.location_ids) {
        if (!this.locations.has(locId)) {
          warnings.push(`Referenced location ${locId} does not exist in canon`);
        }
      }
    }

    if (eventInput.timeline_id && !this.timelines.has(eventInput.timeline_id)) {
      violations.push(`Referenced timeline ${eventInput.timeline_id} does not exist`);
    }

    if (eventInput.timestamp) {
      const timeline = eventInput.timeline_id ? this.timelines.get(eventInput.timeline_id) : null;
      if (timeline && timeline.start_date && eventInput.timestamp < timeline.start_date) {
        violations.push("Event timestamp is before timeline start");
      }
      if (timeline && timeline.end_date && eventInput.timestamp > timeline.end_date) {
        violations.push("Event timestamp is after timeline end");
      }
    }

    for (const relatedId of eventInput.related_events ?? []) {
      if (!this.events.has(relatedId)) {
        warnings.push(`Related event ${relatedId} not found`);
      }
    }

    const isConsistent = violations.length === 0;

    logger.info("Consistency check completed", {
      isConsistent,
      violations: violations.length,
      warnings: warnings.length,
    });

    return { is_consistent: isConsistent, violations, warnings };
  }

  getCharacters(): Character[] {
    return Array.from(this.characters.values());
  }

  getLocations(): Location[] {
    return Array.from(this.locations.values());
  }

  getTimelines(): Timeline[] {
    return Array.from(this.timelines.values());
  }

  getMysteries(status?: Mystery["status"]): Mystery[] {
    const mysteries = Array.from(this.mysteries.values());
    if (!status) return mysteries;
    return mysteries.filter((m) => m.status === status);
  }

  getStoryArcs(status?: StoryArc["status"]): StoryArc[] {
    const arcs = Array.from(this.storyArcs.values());
    if (!status) return arcs;
    return arcs.filter((a) => a.status === status);
  }

  getEventCount(): number {
    return this.events.size;
  }

  getCharacterCount(): number {
    return this.characters.size;
  }

  private getPrimaryTimelineId(): string | undefined {
    for (const [, timeline] of this.timelines) {
      if (timeline.is_primary) return timeline.id;
    }

    const first = this.timelines.keys().next();
    return first.done ? undefined : first.value;
  }
}

function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
