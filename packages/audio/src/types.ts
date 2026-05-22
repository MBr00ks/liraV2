import { z } from "zod";

export const AudioBusTypeSchema = z.enum(["voice", "ambient", "reaction", "spatial", "music"]);
export type AudioBusType = z.infer<typeof AudioBusTypeSchema>;

export const AudioTrackSchema = z.object({
  id: z.string(),
  bus: AudioBusTypeSchema,
  src: z.string(),
  volume: z.number().min(0).max(1).default(1),
  loop: z.boolean().default(false),
  spatial_position: z.object({ x: z.number(), y: z.number(), z: z.number() }).optional(),
  started_at: z.string().optional(),
  duration_ms: z.number().optional(),
});
export type AudioTrack = z.infer<typeof AudioTrackSchema>;

export const ReactionSoundSchema = z.object({
  type: z.string(),
  files: z.array(z.string()),
  weight: z.number().min(0).max(1).default(1),
  cooldown_ms: z.number().default(0),
  interrupt_tts: z.boolean().default(false),
});
export type ReactionSound = z.infer<typeof ReactionSoundSchema>;

export const AudioMixerConfigSchema = z.object({
  sample_rate: z.number().default(48000),
  voice_bus_volume: z.number().min(0).max(1).default(1),
  ambient_bus_volume: z.number().min(0).max(1).default(0.3),
  reaction_bus_volume: z.number().min(0).max(1).default(0.8),
  spatial_bus_volume: z.number().min(0).max(1).default(0.5),
  music_bus_volume: z.number().min(0).max(1).default(0.6),
  ducking_amount: z.number().min(0).max(1).default(0.3),
  crossfade_duration_ms: z.number().default(500),
  max_concurrent_tracks: z.number().default(16),
});
export type AudioMixerConfig = z.infer<typeof AudioMixerConfigSchema>;

export const AudioStateSchema = z.enum([
  "idle",
  "playing",
  "paused",
  "stopped",
  "ducking",
  "crossfading",
  "error",
]);
export type AudioState = z.infer<typeof AudioStateSchema>;

export const BreathingIntensitySchema = z.enum(["calm", "normal", "excited", "nervous", "holding"]);
export type BreathingIntensity = z.infer<typeof BreathingIntensitySchema>;
