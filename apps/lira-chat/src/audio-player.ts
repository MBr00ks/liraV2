export class AudioPlayer {
  private audio: HTMLAudioElement | null = null;
  private _interrupted = false;

  async enqueue(wavBase64: string, _seq?: number): Promise<void> {
    if (this._interrupted) return;
    try {
      // Build a data URL and use native <audio> for reliable playback
      const url = `data:audio/wav;base64,${wavBase64}`;
      if (this.audio) {
        this.audio.pause();
        this.audio.src = "";
      }
      this.audio = new Audio(url);
      await this.audio.play();
    } catch (e) {
      console.error("AudioPlayer: playback failed", e);
    }
  }

  interrupt(): void {
    this._interrupted = true;
    if (this.audio) {
      this.audio.pause();
      this.audio.src = "";
      this.audio = null;
    }
    this._interrupted = false;
  }
}
