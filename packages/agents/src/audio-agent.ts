import { z } from "zod";
import { BaseAgent } from "./base-agent";
import { AgentConfig, AgentResult, AgentInput } from "./types";

const AudioInputSchema = z.object({
  text: z.string(),
  context: z.object({
    action: z.enum(["speak", "play_reaction", "set_ambient", "set_volume", "crossfade", "breathe", "stop"]).default("speak"),
    tts_voice: z.string().optional(),
    tts_speed: z.number().min(0.5).max(2.0).optional(),
    tts_pitch: z.number().min(-12).max(12).optional(),
    reaction_type: z.string().optional(),
    ambient_track: z.string().optional(),
    bus: z.enum(["voice", "ambient", "reaction", "spatial", "music"]).optional(),
    volume: z.number().min(0).max(1).optional(),
    intensity: z.enum(["calm", "normal", "excited", "nervous", "holding"]).optional(),
  }).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});

const AudioOutputSchema = z.object({
  success: z.boolean(),
  action: z.string(),
  track_id: z.string().optional(),
  message: z.string(),
  metadata: z.record(z.unknown()).default({}),
});

export class AudioAgent extends BaseAgent {
  constructor() {
    const config: AgentConfig = {
      id: "audio-agent",
      type: "audio",
      name: "Audio Agent",
      description: "Manages TTS control, reaction sound selection, and ambient audio",
      permissions: ["read_memory", "tts_control", "audio_control", "ambient_control"],
      tools: [
        {
          name: "speak",
          description: "Generate speech via TTS",
          parameters: { text: "string", voice: "string", speed: "number" },
          required_permissions: ["tts_control"],
        },
        {
          name: "play_reaction",
          description: "Play a reaction sound",
          parameters: { type: "string" },
          required_permissions: ["audio_control"],
        },
        {
          name: "set_ambient",
          description: "Set or change ambient audio track",
          parameters: { track: "string", volume: "number" },
          required_permissions: ["ambient_control"],
        },
        {
          name: "set_volume",
          description: "Adjust volume on a specific audio bus",
          parameters: { bus: "string", level: "number" },
          required_permissions: ["audio_control"],
        },
        {
          name: "set_breathing",
          description: "Control breathing layer intensity",
          parameters: { intensity: "string" },
          required_permissions: ["audio_control"],
        },
      ],
      max_tokens: 2048,
      temperature: 0.3,
      system_prompt: `You are Lira's audio agent. You manage the audio subsystem:
- TTS voice generation (Kokoro, XTTSv2)
- Reaction sound selection and timing
- Ambient audio management
- Breathing layer control
- Audio bus volume mixing
- Crossfade between tracks

Coordinate audio timing with the TTS pipeline. Reactions should play during natural pauses.
Breathing should be subtle and context-aware. Ambient audio sets the scene mood.
Never interrupt active voice speech with non-critical sounds.`,
      fallback_message: "The audio system is having trouble right now. I'll try again shortly.",
    };

    super(config);
  }

  async execute(input: AgentInput): Promise<AgentResult> {
    const startTime = Date.now();

    try {
      this.logExecution(input);
      const validated = AudioInputSchema.parse(input);

      this.logger.info("Audio task received", {
        action: validated.context.action,
        bus: validated.context.bus,
        hasVoice: !!validated.context.tts_voice,
      });

      const result = await this.processAudioTask(validated);
      const latency = Date.now() - startTime;

      return this.buildResult(result.message, {
        action: result.action,
        track_id: result.track_id,
        metadata: result.metadata,
      }, latency);
    } catch (error) {
      return this.handleError(error, input);
    }
  }

  private async processAudioTask(input: z.infer<typeof AudioInputSchema>): Promise<z.infer<typeof AudioOutputSchema>> {
    const { context } = input;

    switch (context.action) {
      case "speak":
        return this.handleSpeak(input);
      case "play_reaction":
        return this.handlePlayReaction(context);
      case "set_ambient":
        return this.handleSetAmbient(context);
      case "set_volume":
        return this.handleSetVolume(context);
      case "crossfade":
        return this.handleCrossfade(context);
      case "breathe":
        return this.handleBreathe(context);
      case "stop":
        return this.handleStop(context);
      default:
        return {
          success: false,
          action: context.action,
          message: `Unknown audio action: ${context.action}`,
          metadata: {},
        };
    }
  }

  private handleSpeak(input: z.infer<typeof AudioInputSchema>): z.infer<typeof AudioOutputSchema> {
    const { text, context } = input;
    const voice = context.tts_voice ?? "bf_isabella";
    const speed = context.tts_speed ?? 1.0;
    const pitch = context.tts_pitch ?? 0;

    this.logger.info("TTS request queued", { voice, speed, pitch, textLength: text.length });

    return {
      success: true,
      action: "speak",
      message: `TTS queued: "${text.slice(0, 50)}..."`,
      metadata: { voice, speed, pitch },
    };
  }

  private handlePlayReaction(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    const reactionType = context.reaction_type ?? "giggle";

    this.logger.info("Reaction sound requested", { type: reactionType });

    return {
      success: true,
      action: "play_reaction",
      message: `Playing reaction: ${reactionType}`,
      metadata: { reaction_type: reactionType },
    };
  }

  private handleSetAmbient(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    const track = context.ambient_track ?? "default";
    const volume = context.volume ?? 0.3;

    this.logger.info("Ambient track changed", { track, volume });

    return {
      success: true,
      action: "set_ambient",
      message: `Ambient track set to: ${track}`,
      metadata: { track, volume },
    };
  }

  private handleSetVolume(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    const bus = context.bus ?? "voice";
    const volume = context.volume ?? 1.0;

    this.logger.info("Volume changed", { bus, volume });

    return {
      success: true,
      action: "set_volume",
      message: `Volume set to ${volume} on ${bus} bus`,
      metadata: { bus, volume },
    };
  }

  private handleCrossfade(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    this.logger.info("Crossfade requested", { bus: context.bus });

    return {
      success: true,
      action: "crossfade",
      message: "Crossfade initiated",
      metadata: { bus: context.bus },
    };
  }

  private handleBreathe(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    const intensity = context.intensity ?? "normal";

    this.logger.info("Breathing intensity set", { intensity });

    return {
      success: true,
      action: "breathe",
      message: `Breathing intensity set to: ${intensity}`,
      metadata: { intensity },
    };
  }

  private handleStop(context: z.infer<typeof AudioInputSchema>["context"]): z.infer<typeof AudioOutputSchema> {
    const bus = context.bus ?? "voice";

    this.logger.info("Audio stop requested", { bus });

    return {
      success: true,
      action: "stop",
      message: `Stopped audio on ${bus} bus`,
      metadata: { bus },
    };
  }
}
