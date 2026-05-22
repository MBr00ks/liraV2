import {
  AudioBusType,
  AudioTrack,
  AudioMixerConfig,
  AudioState,
  AudioMixerConfigSchema,
  AudioTrackSchema,
} from "./types";
import { get_logger } from "./logging";

const logger = get_logger("audio-mixer");

interface ActiveTrack {
  track: AudioTrack;
  source: AudioBufferSourceNode | OscillatorNode | null;
  gainNode: GainNode;
  state: AudioState;
}

interface BusState {
  gainNode: GainNode;
  tracks: Map<string, ActiveTrack>;
}

export class AudioMixer {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private buses: Map<AudioBusType, BusState> = new Map();
  private config: AudioMixerConfig;
  private activeTracks: Map<string, ActiveTrack> = new Map();
  private musicDuckGain: GainNode | null = null;
  private isInitialized = false;

  constructor(config: Partial<AudioMixerConfig> = {}) {
    const parsed = AudioMixerConfigSchema.parse(config);
    this.config = parsed;
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    this.ctx = new AudioContext({ sampleRate: this.config.sample_rate });
    this.masterGain = this.ctx.createGain();
    this.masterGain.connect(this.ctx.destination);

    this.musicDuckGain = this.ctx.createGain();
    this.musicDuckGain.gain.value = this.config.music_bus_volume;

    const busTypes: AudioBusType[] = ["voice", "ambient", "reaction", "spatial", "music"];
    const defaultVolumes: Record<AudioBusType, number> = {
      voice: this.config.voice_bus_volume,
      ambient: this.config.ambient_bus_volume,
      reaction: this.config.reaction_bus_volume,
      spatial: this.config.spatial_bus_volume,
      music: this.config.music_bus_volume,
    };

    for (const busType of busTypes) {
      const gainNode = this.ctx.createGain();
      gainNode.gain.value = defaultVolumes[busType];
      gainNode.connect(this.masterGain);

      this.buses.set(busType, {
        gainNode,
        tracks: new Map(),
      });
    }

    this.isInitialized = true;
    logger.info("AudioMixer initialized", { sampleRate: this.config.sample_rate });
  }

  async play(trackInput: Omit<AudioTrack, "id" | "started_at">): Promise<string> {
    this.ensureInitialized();

    const track = AudioTrackSchema.parse({
      ...trackInput,
      id: generateTrackId(),
      started_at: new Date().toISOString(),
    });

    const bus = this.buses.get(track.bus);
    if (!bus) {
      throw new Error(`Unknown bus type: ${track.bus}`);
    }

    if (this.activeTracks.size >= this.config.max_concurrent_tracks) {
      logger.warn("Max concurrent tracks reached, stopping oldest");
      const oldest = this.findOldestTrack();
      if (oldest) this.stop(oldest);
    }

    const gainNode = this.ctx!.createGain();
    gainNode.gain.value = track.volume;
    gainNode.connect(bus.gainNode);

    const activeTrack: ActiveTrack = {
      track,
      source: null,
      gainNode,
      state: "playing",
    };

    try {
      const source = await this.loadAndPlay(track, gainNode);
      activeTrack.source = source;

      this.activeTracks.set(track.id, activeTrack);
      bus.tracks.set(track.id, activeTrack);

      if (track.bus === "voice") {
        await this.duckMusic(0.3);
      }

      logger.info("Track started", { trackId: track.id, bus: track.bus });
      return track.id;
    } catch (error) {
      gainNode.disconnect();
      logger.error("Failed to play track", { trackId: track.id, error: String(error) });
      throw error;
    }
  }

  stop(trackId: string): void {
    const active = this.activeTracks.get(trackId);
    if (!active) {
      logger.warn("Track not found", { trackId });
      return;
    }

    if (active.source) {
      try {
        if ("stop" in active.source) {
          (active.source as AudioBufferSourceNode).stop();
        }
      } catch {
        // Source may already be stopped
      }
    }

    active.gainNode.disconnect();
    this.activeTracks.delete(trackId);

    const bus = this.buses.get(active.track.bus);
    if (bus) {
      bus.tracks.delete(trackId);
    }

    active.state = "stopped";
    logger.info("Track stopped", { trackId });

    if (active.track.bus === "voice" && !this.hasVoiceTracks()) {
      this.unduckMusic();
    }
  }

  setVolume(busType: AudioBusType, level: number): void {
    this.ensureInitialized();

    const clamped = Math.max(0, Math.min(1, level));
    const bus = this.buses.get(busType);
    if (!bus) {
      throw new Error(`Unknown bus type: ${busType}`);
    }

    bus.gainNode.gain.setTargetAtTime(clamped, this.ctx!.currentTime, 0.01);
    logger.info("Bus volume changed", { bus: busType, level: clamped });
  }

  async duckMusic(amount: number): Promise<void> {
    this.ensureInitialized();

    const musicBus = this.buses.get("music");
    if (!musicBus) return;

    const currentVolume = this.config.music_bus_volume;
    const duckedVolume = Math.max(0, currentVolume - amount);

    musicBus.gainNode.gain.setTargetAtTime(duckedVolume, this.ctx!.currentTime, 0.1);
    logger.info("Music ducked", { amount, newVolume: duckedVolume });
  }

  async unduckMusic(): Promise<void> {
    this.ensureInitialized();

    const musicBus = this.buses.get("music");
    if (!musicBus) return;

    musicBus.gainNode.gain.setTargetAtTime(
      this.config.music_bus_volume,
      this.ctx!.currentTime,
      0.3,
    );
    logger.info("Music unducked");
  }

  async crossfade(fromTrackId: string, toTrackInput: Omit<AudioTrack, "id" | "started_at">, durationMs?: number): Promise<string> {
    this.ensureInitialized();

    const fromTrack = this.activeTracks.get(fromTrackId);
    if (!fromTrack) {
      throw new Error(`Source track not found: ${fromTrackId}`);
    }

    const duration = durationMs ?? this.config.crossfade_duration_ms;
    const now = this.ctx!.currentTime;
    const durationSec = duration / 1000;

    fromTrack.gainNode.gain.setTargetAtTime(0, now, durationSec * 0.3);

    const toTrackId = await this.play(toTrackInput);
    const toTrack = this.activeTracks.get(toTrackId);

    if (toTrack) {
      toTrack.gainNode.gain.setValueAtTime(0, now);
      toTrack.gainNode.gain.setTargetAtTime(toTrackInput.volume, now + 0.01, durationSec * 0.3);
    }

    setTimeout(() => {
      this.stop(fromTrackId);
    }, duration);

    logger.info("Crossfade initiated", { from: fromTrackId, to: toTrackId, durationMs: duration });
    return toTrackId;
  }

  getState(): AudioState {
    if (!this.isInitialized) return "idle";

    const hasPlaying = Array.from(this.activeTracks.values()).some(
      (t) => t.state === "playing",
    );

    return hasPlaying ? "playing" : "idle";
  }

  getActiveTracks(): AudioTrack[] {
    return Array.from(this.activeTracks.values()).map((t) => t.track);
  }

  async dispose(): Promise<void> {
    for (const trackId of Array.from(this.activeTracks.keys())) {
      this.stop(trackId);
    }

    if (this.ctx) {
      await this.ctx.close();
      this.ctx = null;
    }

    this.isInitialized = false;
    logger.info("AudioMixer disposed");
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error("AudioMixer not initialized. Call initialize() first.");
    }
  }

  private hasVoiceTracks(): boolean {
    return Array.from(this.activeTracks.values()).some(
      (t) => t.track.bus === "voice" && t.state === "playing",
    );
  }

  private findOldestTrack(): string | null {
    let oldest: { id: string; time: number } | null = null;

    for (const [id, track] of this.activeTracks) {
      const startedAt = track.track.started_at
        ? new Date(track.track.started_at).getTime()
        : Date.now();

      if (!oldest || startedAt < oldest.time) {
        oldest = { id, time: startedAt };
      }
    }

    return oldest?.id ?? null;
  }

  private async loadAndPlay(
    track: AudioTrack,
    gainNode: GainNode,
  ): Promise<AudioBufferSourceNode | OscillatorNode> {
    if (!this.ctx) throw new Error("AudioContext not available");

    if (track.src.startsWith("osc:")) {
      return this.playOscillator(track, gainNode);
    }

    return this.playBuffer(track, gainNode);
  }

  private async playBuffer(
    track: AudioTrack,
    gainNode: GainNode,
  ): Promise<AudioBufferSourceNode> {
    if (!this.ctx) throw new Error("AudioContext not available");

    const response = await fetch(track.src);
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await this.ctx.decodeAudioData(arrayBuffer);

    const source = this.ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.loop = track.loop;
    source.connect(gainNode);
    source.start();

    if (!track.loop) {
      source.onended = () => {
        this.stop(track.id);
      };
    }

    return source;
  }

  private playOscillator(
    track: AudioTrack,
    gainNode: GainNode,
  ): OscillatorNode {
    if (!this.ctx) throw new Error("AudioContext not available");

    const params = track.src.replace("osc:", "").split(",");
    const frequency = parseFloat(params[0] ?? "440");
    const type = (params[1] ?? "sine") as OscillatorType;

    const oscillator = this.ctx.createOscillator();
    oscillator.type = type;
    oscillator.frequency.value = frequency;
    oscillator.connect(gainNode);
    oscillator.start();

    return oscillator;
  }
}

function generateTrackId(): string {
  return `track_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
