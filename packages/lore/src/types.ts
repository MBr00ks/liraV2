import { z } from "zod";

export const LoreEntrySchema = z.object({
  id: z.string(),
  title: z.string(),
  content: z.string(),
  category: z.enum(["character", "location", "event", "artifact", "faction", "concept"]),
  tags: z.array(z.string()).default([]),
  created_at: z.string(),
  updated_at: z.string(),
  canon_verified: z.boolean().default(false),
  importance: z.number().min(1).max(5).default(3),
  metadata: z.record(z.unknown()).default({}),
});
export type LoreEntry = z.infer<typeof LoreEntrySchema>;

export const CharacterSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  aliases: z.array(z.string()).default([]),
  relationships: z.array(z.object({
    character_id: z.string(),
    relationship_type: z.string(),
    description: z.string().optional(),
  })).default([]),
  first_appearance: z.string().optional(),
  last_appearance: z.string().optional(),
  status: z.enum(["active", "inactive", "deceased", "unknown"]).default("active"),
  attributes: z.record(z.unknown()).default({}),
  lore_entries: z.array(z.string()).default([]),
});
export type Character = z.infer<typeof CharacterSchema>;

export const LocationSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  type: z.enum(["interior", "exterior", "dimensional", "abstract"]).default("interior"),
  parent_location: z.string().optional(),
  connected_locations: z.array(z.string()).default([]),
  events: z.array(z.string()).default([]),
  attributes: z.record(z.unknown()).default({}),
});
export type Location = z.infer<typeof LocationSchema>;

export const TimelineSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  events: z.array(z.string()).default([]),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  is_primary: z.boolean().default(false),
});
export type Timeline = z.infer<typeof TimelineSchema>;

export const CanonEventSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  timeline_id: z.string(),
  character_ids: z.array(z.string()).default([]),
  location_ids: z.array(z.string()).default([]),
  timestamp: z.string().optional(),
  era: z.string().optional(),
  is_confirmed: z.boolean().default(true),
  related_events: z.array(z.string()).default([]),
  mystery_ids: z.array(z.string()).default([]),
  metadata: z.record(z.unknown()).default({}),
});
export type CanonEvent = z.infer<typeof CanonEventSchema>;

export const StoryArcSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  event_ids: z.array(z.string()).default([]),
  status: z.enum(["planned", "active", "resolved", "abandoned"]).default("planned"),
  characters_involved: z.array(z.string()).default([]),
  themes: z.array(z.string()).default([]),
  resolution: z.string().optional(),
});
export type StoryArc = z.infer<typeof StoryArcSchema>;

export const MysterySchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  clues: z.array(z.object({
    id: z.string(),
    description: z.string(),
    discovered: z.boolean().default(false),
    source_event: z.string().optional(),
  })).default([]),
  status: z.enum(["hidden", "hinted", "active", "resolved"]).default("hidden"),
  resolution: z.string().optional(),
  resolved_at: z.string().optional(),
  related_event_ids: z.array(z.string()).default([]),
});
export type Mystery = z.infer<typeof MysterySchema>;
