import { ReactionSound, AudioTrack } from "./types";
import { AudioMixer } from "./audio-mixer";
import { get_logger } from "./logging";

const logger = get_logger("reaction-engine");

interface QueuedReaction {
  id: string;
  type: string;
  delayMs: number;
  timeout: ReturnType<typeof setTimeout> | null;
}

interface ReactionMapping {
  [key: string]: ReactionSound;
}

const DEFAULT_REACTION_MAPPING: ReactionMapping = {
  giggle: {
    type: "giggle",
    files: ["audio/reactions/giggle_01.wav", "audio/reactions/giggle_02.wav", "audio/reactions/giggle_03.wav"],
    weight: 1,
    cooldown_ms: 3000,
    interrupt_tts: false,
  },
  sigh: {
    type: "sigh",
    files: ["audio/reactions/sigh_01.wav", "audio/reactions/sigh_02.wav"],
    weight: 1,
    cooldown_ms: 5000,
    interrupt_tts: false,
  },
  gasp: {
    type: "gasp",
    files: ["audio/reactions/gasp_01.wav", "audio/reactions/gasp_02.wav"],
    weight: 1,
    cooldown_ms: 4000,
    interrupt_tts: true,
  },
  moan: {
    type: "moan",
    files: ["audio/reactions/moan_01.wav", "audio/reactions/moan_02.wav"],
    weight: 1,
    cooldown_ms: 6000,
    interrupt_tts: false,
  },
  breath: {
    type: "breath",
    files: ["audio/reactions/breath_01.wav", "audio/reactions/breath_02.wav"],
    weight: 1,
    cooldown_ms: 2000,
    interrupt_tts: false,
  },
  footsteps: {
    type: "footsteps",
    files: ["audio/reactions/footsteps_01.wav", "audio/reactions/footsteps_02.wav"],
    weight: 0.7,
    cooldown_ms: 1000,
    interrupt_tts: false,
  },
  laugh: {
    type: "laugh",
    files: ["audio/reactions/laugh_01.wav", "audio/reactions/laugh_02.wav", "audio/reactions/laugh_03.wav"],
    weight: 1,
    cooldown_ms: 5000,
    interrupt_tts: false,
  },
  hum: {
    type: "hum",
    files: ["audio/reactions/hum_01.wav"],
    weight: 0.5,
    cooldown_ms: 8000,
    interrupt_tts: false,
  },
};

export class ReactionEngine {
  private mixer: AudioMixer;
  private mapping: ReactionMapping;
  private queuedReactions: Map<string, QueuedReaction> = new Map();
  private lastPlayed: Map<string, number> = new Map();
  private counter = 0;

  constructor(mixer: AudioMixer, customMapping?: ReactionMapping) {
    this.mixer = mixer;
    this.mapping = customMapping ?? DEFAULT_REACTION_MAPPING;
  }

  async playReaction(type: string): Promise<string | null> {
    const reaction = this.mapping[type];
    if (!reaction) {
      logger.warn("Unknown reaction type", { type });
      return null;
    }

    const now = Date.now();
    const lastPlayedTime = this.lastPlayed.get(type) ?? 0;

    if (now - lastPlayedTime < reaction.cooldown_ms) {
      logger.debug("Reaction on cooldown", { type, remaining: reaction.cooldown_ms - (now - lastPlayedTime) });
      return null;
    }

    const selectedFile = this.selectFile(reaction);
    if (!selectedFile) {
      logger.warn("No files available for reaction", { type });
      return null;
    }

    try {
      const track: Omit<AudioTrack, "id" | "started_at"> = {
        bus: "reaction",
        src: selectedFile,
        volume: 0.8,
        loop: false,
      };

      const trackId = await this.mixer.play(track);
      this.lastPlayed.set(type, now);

      logger.info("Reaction played", { type, file: selectedFile, trackId });
      return trackId;
    } catch (error) {
      logger.error("Reaction playback failed", { type, error: String(error) });
      return null;
    }
  }

  queueReaction(type: string, delayMs: number = 0): string {
    const id = this.generateReactionId();

    const queued: QueuedReaction = {
      id,
      type,
      delayMs,
      timeout: null,
    };

    if (delayMs > 0) {
      queued.timeout = setTimeout(async () => {
        await this.playReaction(type);
        this.queuedReactions.delete(id);
      }, delayMs);
    } else {
      this.playReaction(type).finally(() => {
        this.queuedReactions.delete(id);
      });
    }

    this.queuedReactions.set(id, queued);
    logger.info("Reaction queued", { id, type, delayMs });
    return id;
  }

  cancelReaction(id: string): void {
    const queued = this.queuedReactions.get(id);
    if (!queued) {
      logger.warn("Reaction not found for cancellation", { id });
      return;
    }

    if (queued.timeout) {
      clearTimeout(queued.timeout);
    }

    this.queuedReactions.delete(id);
    logger.info("Reaction cancelled", { id });
  }

  cancelAllReactions(): void {
    for (const [, queued] of this.queuedReactions) {
      if (queued.timeout) {
        clearTimeout(queued.timeout);
      }
    }

    this.queuedReactions.clear();
    logger.info("All reactions cancelled");
  }

  getQueuedReactions(): QueuedReaction[] {
    return Array.from(this.queuedReactions.values());
  }

  registerReaction(reaction: ReactionSound): void {
    this.mapping[reaction.type] = reaction;
    logger.info("Reaction registered", { type: reaction.type });
  }

  getMapping(): ReactionMapping {
    return { ...this.mapping };
  }

  selectFile(reaction: ReactionSound): string | null {
    if (reaction.files.length === 0) return null;

    if (reaction.files.length === 1) {
      return reaction.files[0];
    }

    const weightedFiles = reaction.files.map((file: string) => {
      const baseWeight = reaction.weight / reaction.files.length;
      const recencyPenalty = this.getRecencyPenalty(reaction.type, file);
      return { file, weight: baseWeight * (1 - recencyPenalty) };
    });

    const totalWeight = weightedFiles.reduce((sum: number, f: { file: string; weight: number }) => sum + f.weight, 0);
    let random = Math.random() * totalWeight;

    for (const { file, weight } of weightedFiles) {
      random -= weight;
      if (random <= 0) return file;
    }

    return weightedFiles[weightedFiles.length - 1]?.file ?? null;
  }

  private getRecencyPenalty(type: string, file: string): number {
    const lastPlayedKey = `${type}:${file}`;
    const lastPlayedTime = this.lastPlayed.get(lastPlayedKey) ?? 0;
    const elapsed = Date.now() - lastPlayedTime;

    if (elapsed < 10000) return 0.5;
    if (elapsed < 30000) return 0.2;
    return 0;
  }

  private generateReactionId(): string {
    this.counter += 1;
    return `reaction_${Date.now()}_${this.counter}`;
  }
}
