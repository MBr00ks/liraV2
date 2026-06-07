export class AudioPlayer {
  private ctx: AudioContext | null = null;
  private queue: Map<number, AudioBuffer> = new Map();
  private nextSeq = 1;
  private playing = false;
  private _interrupted = false;

  private getCtx(): AudioContext {
    if (!this.ctx) this.ctx = new AudioContext();
    return this.ctx;
  }

  async enqueue(wavBase64: string, seq?: number): Promise<void> {
    const binary = atob(wavBase64);
    const array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);
    const audioCtx = this.getCtx();
    const decoded = await audioCtx.decodeAudioData(array.buffer);
    // Use sequence number if provided, otherwise play immediately
    if (seq !== undefined) {
      this.queue.set(seq, decoded);
    } else {
      // No sequence — play immediately at next opportunity
      const key = this.nextSeq++;
      this.queue.set(key, decoded);
    }
    if (!this.playing) this.playNext();
  }

  private playNext(): void {
    if (this._interrupted || this.queue.size === 0) {
      this.playing = false;
      return;
    }
    // Play the next in sequence
    const buf = this.queue.get(this.nextSeq);
    if (!buf) {
      // Missing sequence — wait for it (don't skip ahead)
      this.playing = false;
      return;
    }
    this.queue.delete(this.nextSeq);
    this.nextSeq++;
    this.playing = true;
    const audioCtx = this.getCtx();
    const source = audioCtx.createBufferSource();
    source.buffer = buf;
    source.connect(audioCtx.destination);
    source.onended = () => this.playNext();
    source.start();
  }

  interrupt(): void {
    this._interrupted = true;
    this.queue.clear();
    this.nextSeq = 1;
    if (this.ctx) {
      this.ctx.close();
      this.ctx = null;
    }
    this.playing = false;
    this._interrupted = false;
  }
}
