import { z } from "zod";
import { VisionResult, FaceDetection, FaceDetectionSchema } from "./types";
import { get_logger } from "./logging";

const logger = get_logger("vision-client");

const VisionModelConfigSchema = z.object({
  base_url: z.string().default("http://localhost:11434"),
  model: z.string().default("llava:7b"),
  timeout_ms: z.number().default(30000),
  max_tokens: z.number().default(512),
  temperature: z.number().min(0).max(2).default(0.3),
});
type VisionModelConfig = z.infer<typeof VisionModelConfigSchema>;

export class VisionClient {
  private config: VisionModelConfig;
  private isAvailable = false;

  constructor(config?: Partial<VisionModelConfig>) {
    this.config = VisionModelConfigSchema.parse(config ?? {});
  }

  async initialize(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.base_url}/api/tags`, {
        method: "GET",
        signal: AbortSignal.timeout(this.config.timeout_ms),
      });

      if (response.ok) {
        this.isAvailable = true;
        logger.info("Vision client initialized", { model: this.config.model, baseUrl: this.config.base_url });
      } else {
        this.isAvailable = false;
        logger.warn("Vision service returned non-OK status", { status: response.status });
      }

      return this.isAvailable;
    } catch (error) {
      this.isAvailable = false;
      logger.error("Vision client initialization failed", { error: String(error) });
      return false;
    }
  }

  async analyze(image: string | Buffer): Promise<VisionResult> {
    this.ensureAvailable();

    const prompt = "Describe what you see in this image in detail. Include people, objects, setting, and mood.";

    try {
      const response = await this.callVisionModel(image, prompt);

      const result: VisionResult = {
        id: generateId("vision"),
        timestamp: new Date().toISOString(),
        description: response,
        faces: [],
        people_count: this.estimatePeopleCount(response),
        privacy_safe: true,
        metadata: { model: this.config.model },
      };

      logger.info("Image analysis completed", { resultId: result.id, descriptionLength: response.length });
      return result;
    } catch (error) {
      logger.error("Image analysis failed", { error: String(error) });
      throw error;
    }
  }

  async describe(image: string | Buffer): Promise<string> {
    this.ensureAvailable();

    const prompt = "Provide a concise description of this image, focusing on the main subjects and setting.";

    try {
      const description = await this.callVisionModel(image, prompt);
      logger.info("Image description generated", { descriptionLength: description.length });
      return description;
    } catch (error) {
      logger.error("Image description failed", { error: String(error) });
      throw error;
    }
  }

  async detectFaces(image?: string | Buffer): Promise<FaceDetection> {
    this.ensureAvailable();

    const prompt = "Count the number of faces visible in this image. Return only the count as a number.";

    try {
      const imageInput = image ?? await this.captureFrame();
      const response = await this.callVisionModel(imageInput, prompt);

      const faceCount = this.parseFaceCount(response);

      const result: FaceDetection = {
        face_count: faceCount,
        faces: [],
        processing_time_ms: undefined,
      };

      logger.info("Face detection completed", { faceCount });
      return result;
    } catch (error) {
      logger.error("Face detection failed", { error: String(error) });

      return {
        face_count: 0,
        faces: [],
      };
    }
  }

  async describeWithPrompt(image: string | Buffer, prompt: string): Promise<string> {
    this.ensureAvailable();

    try {
      const response = await this.callVisionModel(image, prompt);
      return response;
    } catch (error) {
      logger.error("Prompted description failed", { error: String(error) });
      throw error;
    }
  }

  getAvailability(): boolean {
    return this.isAvailable;
  }

  getModel(): string {
    return this.config.model;
  }

  private async callVisionModel(image: string | Buffer, prompt: string): Promise<string> {
    const imageBase64 = this.ensureBase64(image);

    const requestBody = {
      model: this.config.model,
      prompt,
      images: [imageBase64],
      stream: false,
      options: {
        temperature: this.config.temperature,
        num_predict: this.config.max_tokens,
      },
    };

    const response = await fetch(`${this.config.base_url}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(this.config.timeout_ms),
    });

    if (!response.ok) {
      throw new Error(`Vision model returned ${response.status}`);
    }

    const data = (await response.json()) as { response: string };
    return data.response;
  }

  private async captureFrame(): Promise<string> {
    throw new Error("Frame capture not implemented. Provide image data directly.");
  }

  private ensureBase64(image: string | Buffer): string {
    if (typeof image === "string" && image.startsWith("data:")) {
      return image.split(",")[1] ?? image;
    }

    if (typeof image === "string") {
      return image;
    }

    return image.toString("base64");
  }

  private ensureAvailable(): void {
    if (!this.isAvailable) {
      throw new Error("Vision client not available. Call initialize() first.");
    }
  }

  private estimatePeopleCount(description: string): number {
    const lower = description.toLowerCase();

    const personPatterns = [
      /(\d+)\s*(?:person|people|human|face)/gi,
      /a\s+(?:group|crowd|couple)/gi,
      /two\s+people/gi,
      /three\s+people/gi,
      /several\s+people/gi,
    ];

    for (const pattern of personPatterns) {
      const match = lower.match(pattern);
      if (match) {
        const number = parseInt(match[0], 10);
        if (!isNaN(number)) return number;

        if (match[0].includes("group")) return 3;
        if (match[0].includes("crowd")) return 5;
        if (match[0].includes("couple")) return 2;
        if (match[0].includes("two")) return 2;
        if (match[0].includes("three")) return 3;
        if (match[0].includes("several")) return 3;
      }
    }

    return 0;
  }

  private parseFaceCount(response: string): number {
    const numbers = response.match(/\d+/g);
    if (numbers && numbers.length > 0) {
      return parseInt(numbers[0], 10);
    }
    return 0;
  }
}

function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
