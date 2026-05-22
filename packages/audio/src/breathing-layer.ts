import { BreathingIntensity, AudioTrack } from "./types";
import { AudioMixer } from "./audio-mixer";
import { get_logger } from "./logging";

const logger = get_logger("breathing-layer");

interface BreathingPattern {
  inhaleMs: number;
  holdMs: number;
  exhaleMs: number;
  pauseMs: number;
  soundProfile: string;
}

const BREATHING_PATTERNS: Record<BreathingIntensity, BreathingPattern> = {
  calm: {
    inhaleMs: 4000,
    holdMs: 1500,
    exhaleMs: 5000,
    pauseMs: 2000,
    soundProfile: "soft_nasal",
  },
  normal: {
    inhaleMs: 3000,
    holdMs: 800,
    exhaleMs: 3500,
    pauseMs: 1000,
    soundProfile: "natural",
  },
  excited: {
    inhaleMs: 1500,
    holdMs: 200,
    exhaleMs: 2000,
    pauseMs: 300,
    soundProfile: "light_quick",
  },
  nervous: {
    inhaleMs: 2000,
    holdMs: 500,
    exhaleMs: 2500,
    pauseMs: 800,
    soundProfile: "shallow",
  },
  holding: {
    inhaleMs: 1000,
    holdMs: 8000,
    exhaleMs: 1500,
    pauseMs: 500,
    soundProfile: "suppressed",
  },
};

export class BreathingLayer {
  private mixer: AudioMixer;
  private currentIntensity: BreathingIntensity = "calm";
  private isRunning = false;
  private currentTrackId: string | null = null;
  private loopTimeout: ReturnType<typeof setTimeout> | null = null;
  private pattern: BreathingPattern = BREATHING_PATTERNS.calm;

  constructor(mixer: AudioMixer) {
    this.mixer = mixer;
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      logger.warn("BreathingLayer already running");
      return;
    }

    this.isRunning = true;
    logger.info("BreathingLayer started", { intensity: this.currentIntensity });
    await this.breathe();
  }

  stop(): void {
    this.isRunning = false;

    if (this.loopTimeout) {
      clearTimeout(this.loopTimeout);
      this.loopTimeout = null;
    }

    if (this.currentTrackId) {
      this.mixer.stop(this.currentTrackId);
      this.currentTrackId = null;
    }

    logger.info("BreathingLayer stopped");
  }

  setIntensity(level: BreathingIntensity): void {
    this.currentIntensity = level;
    this.pattern = BREATHING_PATTERNS[level];
    logger.info("Breathing intensity changed", { intensity: level });
  }

  async breathe(): Promise<void> {
    if (!this.isRunning) return;

    const { inhaleMs, holdMs, exhaleMs, pauseMs, soundProfile } = this.pattern;

    try {
      const inhaleTrack: Omit<AudioTrack, "id" | "started_at"> = {
        bus: "ambient",
        src: `audio/breathing/${soundProfile}_inhale.wav`,
        volume: 0.15,
        loop: false,
      };

      this.currentTrackId = await this.mixer.play(inhaleTrack);

      await this.wait(inhaleMs);
      if (!this.isRunning) return;

      await this.wait(holdMs);
      if (!this.isRunning) return;

      if (this.currentTrackId) {
        this.mixer.stop(this.currentTrackId);
      }

      const exhaleTrack: Omit<AudioTrack, "id" | "started_at"> = {
        bus: "ambient",
        src: `audio/breathing/${soundProfile}_exhale.wav`,
        volume: 0.12,
        loop: false,
      };

      this.currentTrackId = await this.mixer.play(exhaleTrack);

      await this.wait(exhaleMs);
      if (!this.isRunning) return;

      await this.wait(pauseMs);
      if (!this.isRunning) return;

      this.loopTimeout = setTimeout(() => {
        this.breathe();
      }, 50);
    } catch (error) {
      logger.error("Breathing cycle failed, restarting", { error: String(error) });

      if (this.isRunning) {
        this.loopTimeout = setTimeout(() => {
          this.breathe();
        }, 2000);
      }
    }
  }

  async sigh(): Promise<void> {
    if (!this.isRunning) return;

    const previousTimeout = this.loopTimeout;
    if (previousTimeout) {
      clearTimeout(previousTimeout);
    }

    try {
      const sighTrack: Omit<AudioTrack, "id" | "started_at"> = {
        bus: "reaction",
        src: "audio/breathing/sigh.wav",
        volume: 0.25,
        loop: false,
      };

      await this.mixer.play(sighTrack);
      logger.info("Sigh played");

      await this.wait(2000);

      if (this.isRunning) {
        this.breathe();
      }
    } catch (error) {
      logger.error("Sigh playback failed", { error: String(error) });
      if (this.isRunning) {
        this.breathe();
      }
    }
  }

  async hold(): Promise<void> {
    const previousIntensity = this.currentIntensity;
    this.setIntensity("holding");

    logger.info("Breath hold initiated");

    return new Promise<void>((resolve) => {
      const holdDuration = this.pattern.holdMs;

      this.loopTimeout = setTimeout(() => {
        this.setIntensity(previousIntensity);
        logger.info("Breath hold released", { returnedTo: previousIntensity });
        resolve();
      }, holdDuration);
    });
  }

  isBreathing(): boolean {
    return this.isRunning;
  }

  getIntensity(): BreathingIntensity {
    return this.currentIntensity;
  }

  private wait(ms: number): Promise<void> {
    return new Promise((resolve) => {
      this.loopTimeout = setTimeout(resolve, ms);
    });
  }
}
