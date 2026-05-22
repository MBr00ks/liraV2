import { SentimentEstimation } from "./types";
import { get_logger } from "./logging";

const logger = get_logger("sentiment-estimator");

interface AudioFeatures {
  volume: number;
  pitch: number;
  speech_rate: number;
  pause_frequency: number;
  tone_variance: number;
}

interface TextFeatures {
  words: string[];
  exclamation_count: number;
  question_count: number;
  ellipsis_count: number;
  capitalization_ratio: number;
  avg_word_length: number;
}

const MOOD_KEYWORDS: Record<string, string[]> = {
  happy: ["great", "awesome", "love", "wonderful", "amazing", "fantastic", "excited", "happy", "joy", "fun", "yes", "good", "nice"],
  sad: ["sad", "unfortunately", "miss", "sorry", "down", "unhappy", "depressed", "lonely", "hurt", "bad", "no"],
  angry: ["angry", "frustrated", "annoyed", "hate", "terrible", "awful", "worst", "ridiculous", "unacceptable", "damn"],
  surprised: ["wow", "oh", "really", "unexpected", "shocked", "amazed", "incredible", "unbelievable", "what"],
  tired: ["tired", "exhausted", "sleepy", "bored", "fatigued", "drained", "worn", "weary"],
  excited: ["excited", "thrilled", "can't wait", "looking forward", "eager", "enthusiastic", "pumped"],
  stressed: ["stressed", "pressure", "deadline", "overwhelm", "anxious", "worried", "nervous", "busy"],
};

export class SentimentEstimator {
  private history: SentimentEstimation[] = [];
  private currentMood: SentimentEstimation | null = null;
  private maxHistorySize = 100;

  estimateFromAudio(audioFeatures: AudioFeatures): SentimentEstimation {
    const { volume, pitch, speech_rate, pause_frequency, tone_variance } = audioFeatures;

    let mood: SentimentEstimation["mood"] = "neutral";
    let confidence = 0.5;
    const cues: string[] = [];

    if (volume > 0.8 && pitch > 0.7) {
      mood = "excited";
      confidence = 0.7;
      cues.push("high volume and pitch");
    } else if (volume < 0.3 && speech_rate < 0.4) {
      mood = "tired";
      confidence = 0.6;
      cues.push("low volume and slow speech");
    } else if (pause_frequency > 0.7) {
      mood = "stressed";
      confidence = 0.6;
      cues.push("frequent pauses");
    } else if (tone_variance > 0.7) {
      mood = "happy";
      confidence = 0.6;
      cues.push("high tone variance");
    } else if (pitch < 0.3 && volume < 0.4) {
      mood = "sad";
      confidence = 0.5;
      cues.push("low pitch and volume");
    }

    const intensity = this.calculateIntensity(audioFeatures);

    const result: SentimentEstimation = {
      mood,
      confidence,
      intensity,
      source: "audio",
      cues,
      timestamp: new Date().toISOString(),
    };

    this.updateHistory(result);
    logger.info("Audio sentiment estimated", { mood, confidence, cues: cues.length });
    return result;
  }

  estimateFromText(text: string): SentimentEstimation {
    const features = this.extractTextFeatures(text);
    const scores = this.scoreTextMood(features);

    let mood: SentimentEstimation["mood"] = "neutral";
    let maxScore = 0;

    for (const [candidateMood, score] of Object.entries(scores)) {
      if (score > maxScore) {
        maxScore = score;
        mood = candidateMood as SentimentEstimation["mood"];
      }
    }

    const confidence = Math.min(1, maxScore / 3);
    const cues = this.getTextCues(features, mood);
    const intensity = this.calculateTextIntensity(features);

    const result: SentimentEstimation = {
      mood,
      confidence,
      intensity,
      source: "text",
      cues,
      timestamp: new Date().toISOString(),
    };

    this.updateHistory(result);
    logger.info("Text sentiment estimated", { mood, confidence, textLength: text.length });
    return result;
  }

  estimateCombined(audioFeatures: AudioFeatures, text: string): SentimentEstimation {
    const audioResult = this.estimateFromAudio(audioFeatures);
    const textResult = this.estimateFromText(text);

    const audioWeight = 0.4;
    const textWeight = 0.6;

    const combinedConfidence = (audioResult.confidence * audioWeight) + (textResult.confidence * textWeight);
    const combinedIntensity = (audioResult.intensity * audioWeight) + (textResult.intensity * textWeight);

    const mood = combinedConfidence > 0.5
      ? (audioResult.confidence > textResult.confidence ? audioResult.mood : textResult.mood)
      : "neutral";

    const cues = [...new Set([...audioResult.cues, ...textResult.cues])].slice(0, 5);

    const result: SentimentEstimation = {
      mood,
      confidence: combinedConfidence,
      intensity: combinedIntensity,
      source: "combined",
      cues,
      timestamp: new Date().toISOString(),
    };

    this.updateHistory(result);
    return result;
  }

  getMood(): SentimentEstimation | null {
    return this.currentMood;
  }

  getMoodHistory(): SentimentEstimation[] {
    return [...this.history];
  }

  getRecentMood(windowMs: number = 60000): SentimentEstimation | null {
    const cutoff = Date.now() - windowMs;

    const recent = this.history.filter(
      (h) => new Date(h.timestamp).getTime() > cutoff,
    );

    if (recent.length === 0) return null;

    const moodCounts: Record<string, number> = {};
    for (const entry of recent) {
      moodCounts[entry.mood] = (moodCounts[entry.mood] ?? 0) + 1;
    }

    const dominantMood = Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0];
    if (!dominantMood) return null;

    return recent.find((h) => h.mood === dominantMood[0]) ?? null;
  }

  private extractTextFeatures(text: string): TextFeatures {
    const words = text.toLowerCase().split(/\s+/).filter((w) => w.length > 0);
    const exclamationCount = (text.match(/!/g) ?? []).length;
    const questionCount = (text.match(/\?/g) ?? []).length;
    const ellipsisCount = (text.match(/\.{3,}/g) ?? []).length;
    const capitalizedWords = text.split(/\s+/).filter((w) => /^[A-Z]/.test(w) && w.length > 1);
    const capitalizationRatio = words.length > 0 ? capitalizedWords.length / words.length : 0;
    const avgWordLength = words.length > 0 ? words.reduce((sum, w) => sum + w.length, 0) / words.length : 0;

    return {
      words,
      exclamation_count: exclamationCount,
      question_count: questionCount,
      ellipsis_count: ellipsisCount,
      capitalization_ratio: capitalizationRatio,
      avg_word_length: avgWordLength,
    };
  }

  private scoreTextMood(features: TextFeatures): Record<string, number> {
    const scores: Record<string, number> = {};

    for (const [mood, keywords] of Object.entries(MOOD_KEYWORDS)) {
      let score = 0;

      for (const keyword of keywords) {
        const matches = features.words.filter((w) => w.includes(keyword)).length;
        score += matches;
      }

      score += features.exclamation_count * 0.5;
      score += features.ellipsis_count * 0.3;

      scores[mood] = score;
    }

    return scores;
  }

  private getTextCues(features: TextFeatures, mood: string): string[] {
    const cues: string[] = [];

    if (features.exclamation_count > 0) cues.push(`${features.exclamation_count} exclamation(s)`);
    if (features.question_count > 0) cues.push(`${features.question_count} question(s)`);
    if (features.ellipsis_count > 0) cues.push(`${features.ellipsis_count} ellipsis(es)`);
    if (features.capitalization_ratio > 0.3) cues.push("high capitalization");

    const matchedKeywords = MOOD_KEYWORDS[mood]?.filter((kw) =>
      features.words.some((w) => w.includes(kw)),
    ) ?? [];
    if (matchedKeywords.length > 0) {
      cues.push(`keywords: ${matchedKeywords.slice(0, 3).join(", ")}`);
    }

    return cues;
  }

  private calculateIntensity(features: AudioFeatures): number {
    return (
      features.volume * 0.3 +
      Math.abs(features.pitch - 0.5) * 0.3 +
      features.speech_rate * 0.2 +
      features.tone_variance * 0.2
    );
  }

  private calculateTextIntensity(features: TextFeatures): number {
    const exclamationWeight = Math.min(1, features.exclamation_count / 5);
    const capitalizationWeight = features.capitalization_ratio;
    const lengthWeight = Math.min(1, features.avg_word_length / 10);

    return (exclamationWeight * 0.4) + (capitalizationWeight * 0.3) + (lengthWeight * 0.3);
  }

  private updateHistory(result: SentimentEstimation): void {
    this.currentMood = result;
    this.history.push(result);

    if (this.history.length > this.maxHistorySize) {
      this.history = this.history.slice(-this.maxHistorySize);
    }
  }
}
