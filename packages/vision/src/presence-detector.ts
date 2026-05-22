import { PresenceDetection, PrivacyMode, PrivacyConfig, PrivacyConfigSchema } from "./types";
import { VisionClient } from "./vision-client";
import { get_logger } from "./logging";

const logger = get_logger("presence-detector");

interface DetectionHistory {
  timestamp: string;
  personCount: number;
  knownPerson: boolean;
  personId?: string;
}

export class PresenceDetector {
  private visionClient: VisionClient;
  private privacyConfig: PrivacyConfig;
  private detectionHistory: DetectionHistory[] = [];
  private isMikePresent = false;
  private mikeLastSeen: string | null = null;
  private additionalPeopleCount = 0;
  private currentPrivacyMode: PrivacyMode = "full";
  private detectionInterval: ReturnType<typeof setInterval> | null = null;
  private maxHistorySize = 50;

  constructor(visionClient: VisionClient, config?: Partial<PrivacyConfig>) {
    this.visionClient = visionClient;
    this.privacyConfig = PrivacyConfigSchema.parse(config ?? {});
    this.currentPrivacyMode = this.privacyConfig.mode;
  }

  async detectPresence(): Promise<PresenceDetection> {
    try {
      const faceDetection = await this.visionClient.detectFaces();

      const personCount = faceDetection.face_count;
      let knownPerson = false;
      let personId: string | undefined;

      for (const face of faceDetection.faces) {
        if (face.is_known) {
          knownPerson = true;
          personId = face.person_id;
          break;
        }
      }

      this.isMikePresent = knownPerson && personId === "mike";
      if (this.isMikePresent) {
        this.mikeLastSeen = new Date().toISOString();
      }

      this.additionalPeopleCount = Math.max(0, personCount - 1);

      this.updatePrivacyMode();

      const historyEntry: DetectionHistory = {
        timestamp: new Date().toISOString(),
        personCount,
        knownPerson,
        personId,
      };
      this.addToHistory(historyEntry);

      const result: PresenceDetection = {
        is_present: this.isMikePresent,
        confidence: this.calculateConfidence(),
        person_count: personCount,
        known_person: knownPerson,
        person_id: personId,
        last_seen: this.mikeLastSeen ?? undefined,
        duration_seconds: this.calculateDuration(),
      };

      if (this.privacyConfig.log_detections) {
        logger.info("Presence detection completed", {
          mikePresent: this.isMikePresent,
          personCount,
          privacyMode: this.currentPrivacyMode,
        });
      }

      return result;
    } catch (error) {
      logger.error("Presence detection failed", { error: String(error) });

      return {
        is_present: false,
        confidence: 0,
        person_count: 0,
        known_person: false,
        last_seen: this.mikeLastSeen ?? undefined,
      };
    }
  }

  async countPeople(): Promise<number> {
    try {
      const faceDetection = await this.visionClient.detectFaces();
      return faceDetection.face_count;
    } catch (error) {
      logger.error("People count failed", { error: String(error) });
      return 0;
    }
  }

  async detectAdditionalVoices(): Promise<number> {
    if (!this.privacyConfig.detect_additional_voices) {
      return 0;
    }

    const personCount = await this.countPeople();
    return Math.max(0, personCount - 1);
  }

  getPrivacyMode(): PrivacyMode {
    return this.currentPrivacyMode;
  }

  setPrivacyMode(mode: PrivacyMode): void {
    this.currentPrivacyMode = mode;
    logger.info("Privacy mode manually set", { mode });
  }

  isPublicSafe(): boolean {
    return this.currentPrivacyMode === "public_safe";
  }

  shouldRestrictBehavior(): boolean {
    return this.currentPrivacyMode === "public_safe" || this.currentPrivacyMode === "restricted";
  }

  getMikePresence(): boolean {
    return this.isMikePresent;
  }

  getAdditionalPeopleCount(): number {
    return this.additionalPeopleCount;
  }

  getDetectionHistory(): DetectionHistory[] {
    return [...this.detectionHistory];
  }

  startPeriodicDetection(intervalMs: number = 5000): void {
    if (this.detectionInterval) {
      this.stopPeriodicDetection();
    }

    this.detectionInterval = setInterval(async () => {
      await this.detectPresence();
    }, intervalMs);

    logger.info("Periodic presence detection started", { intervalMs });
  }

  stopPeriodicDetection(): void {
    if (this.detectionInterval) {
      clearInterval(this.detectionInterval);
      this.detectionInterval = null;
      logger.info("Periodic presence detection stopped");
    }
  }

  private updatePrivacyMode(): void {
    if (!this.privacyConfig.auto_public_safe) return;

    const threshold = this.privacyConfig.public_safe_threshold;

    if (this.additionalPeopleCount >= threshold) {
      if (this.currentPrivacyMode !== "public_safe") {
        this.currentPrivacyMode = "public_safe";
        logger.warn("Auto-switched to public_safe mode", { additionalPeople: this.additionalPeopleCount });
      }
    } else if (this.additionalPeopleCount > 0) {
      if (this.currentPrivacyMode !== "restricted") {
        this.currentPrivacyMode = "restricted";
        logger.info("Auto-switched to restricted mode", { additionalPeople: this.additionalPeopleCount });
      }
    } else {
      if (this.currentPrivacyMode !== "full") {
        this.currentPrivacyMode = "full";
        logger.info("Auto-switched to full privacy mode");
      }
    }
  }

  private calculateConfidence(): number {
    if (this.detectionHistory.length === 0) return 0;

    const recentHistory = this.detectionHistory.slice(-5);
    const mikePresenceCount = recentHistory.filter(
      (h) => h.knownPerson && h.personId === "mike",
    ).length;

    return mikePresenceCount / recentHistory.length;
  }

  private calculateDuration(): number | undefined {
    if (!this.mikeLastSeen || this.detectionHistory.length === 0) return undefined;

    const firstDetection = this.detectionHistory.find(
      (h) => h.knownPerson && h.personId === "mike",
    );

    if (!firstDetection) return undefined;

    const firstTime = new Date(firstDetection.timestamp).getTime();
    const now = Date.now();

    return Math.round((now - firstTime) / 1000);
  }

  private addToHistory(entry: DetectionHistory): void {
    this.detectionHistory.push(entry);

    if (this.detectionHistory.length > this.maxHistorySize) {
      this.detectionHistory = this.detectionHistory.slice(-this.maxHistorySize);
    }
  }
}
