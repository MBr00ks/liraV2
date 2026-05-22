import { z } from "zod";

export const VisionResultSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  description: z.string().optional(),
  faces: z.array(z.object({
    bounding_box: z.object({ x: z.number(), y: z.number(), width: z.number(), height: z.number() }),
    confidence: z.number().min(0).max(1),
    attributes: z.record(z.unknown()).optional(),
  })).default([]),
  people_count: z.number().default(0),
  privacy_safe: z.boolean().default(true),
  metadata: z.record(z.unknown()).default({}),
});
export type VisionResult = z.infer<typeof VisionResultSchema>;

export const PresenceDetectionSchema = z.object({
  is_present: z.boolean(),
  confidence: z.number().min(0).max(1),
  person_count: z.number().default(0),
  known_person: z.boolean().default(false),
  person_id: z.string().optional(),
  last_seen: z.string().optional(),
  duration_seconds: z.number().optional(),
});
export type PresenceDetection = z.infer<typeof PresenceDetectionSchema>;

export const SentimentEstimationSchema = z.object({
  mood: z.enum(["neutral", "happy", "sad", "angry", "surprised", "fearful", "disgusted", "tired", "excited", "stressed"]).default("neutral"),
  confidence: z.number().min(0).max(1),
  intensity: z.number().min(0).max(1).default(0.5),
  source: z.enum(["audio", "text", "combined"]).default("text"),
  cues: z.array(z.string()).default([]),
  timestamp: z.string(),
});
export type SentimentEstimation = z.infer<typeof SentimentEstimationSchema>;

export const FaceDetectionSchema = z.object({
  face_count: z.number().default(0),
  faces: z.array(z.object({
    bounding_box: z.object({ x: z.number(), y: z.number(), width: z.number(), height: z.number() }),
    confidence: z.number().min(0).max(1),
    landmarks: z.array(z.object({ x: z.number(), y: z.number() })).optional(),
    is_known: z.boolean().default(false),
    person_id: z.string().optional(),
  })).default([]),
  processing_time_ms: z.number().optional(),
});
export type FaceDetection = z.infer<typeof FaceDetectionSchema>;

export const PrivacyModeSchema = z.enum(["full", "restricted", "public_safe", "off"]);
export type PrivacyMode = z.infer<typeof PrivacyModeSchema>;

export const PrivacyConfigSchema = z.object({
  mode: PrivacyModeSchema.default("full"),
  store_frames: z.boolean().default(false),
  blur_faces: z.boolean().default(false),
  detect_additional_voices: z.boolean().default(true),
  auto_public_safe: z.boolean().default(true),
  public_safe_threshold: z.number().min(1).default(2),
  log_detections: z.boolean().default(true),
  anonymize_logs: z.boolean().default(true),
});
export type PrivacyConfig = z.infer<typeof PrivacyConfigSchema>;
