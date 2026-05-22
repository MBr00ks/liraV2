import { z } from "zod";
import { BaseAgent } from "./base-agent";
import { AgentConfig, AgentResult, AgentInput } from "./types";

const ImageInputSchema = z.object({
  text: z.string(),
  context: z.object({
    image_type: z.enum(["character_art", "concept_art", "scene", "reference"]).default("character_art"),
    style: z.string().optional(),
    dimensions: z.object({ width: z.number(), height: z.number() }).optional(),
    negative_prompt: z.string().optional(),
    seed: z.number().optional(),
    character_reference: z.string().optional(),
  }).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});

const ImageOutputSchema = z.object({
  image_url: z.string().optional(),
  prompt_used: z.string(),
  negative_prompt_used: z.string().optional(),
  generation_time_ms: z.number().optional(),
  model_used: z.string().optional(),
  seed_used: z.number().optional(),
  error: z.string().optional(),
});

export class ImageAgent extends BaseAgent {
  private comfyUiUrl: string;

  constructor(comfyUiUrl?: string) {
    const config: AgentConfig = {
      id: "image-agent",
      type: "image",
      name: "Image Agent",
      description: "Handles ComfyUI image generation, character art, and concept art",
      permissions: ["read_memory", "read_lore", "image_generation"],
      tools: [
        {
          name: "generate_image",
          description: "Generate an image using ComfyUI",
          parameters: { prompt: "string", negative_prompt: "string", steps: "number" },
          required_permissions: ["image_generation"],
        },
        {
          name: "get_workflow",
          description: "Retrieve a ComfyUI workflow by name",
          parameters: { workflow_name: "string" },
          required_permissions: ["image_generation"],
        },
        {
          name: "get_character_reference",
          description: "Get character reference data for consistent generation",
          parameters: { character_name: "string" },
          required_permissions: ["read_lore"],
        },
      ],
      max_tokens: 2048,
      temperature: 0.5,
      system_prompt: `You are Lira's image generation agent. You manage ComfyUI pipelines for:
- Character art generation
- Concept art and scene visualization
- Reference image creation
- Style-consistent artwork

Always use established character references from the lore database for consistency.
If ComfyUI is unavailable, explain that the visual workshop is offline rather than crashing.
Provide detailed prompts that capture the artistic intent.`,
      fallback_message: "The visual workshop is currently offline. I'll let you know when it's available again.",
    };

    super(config);
    this.comfyUiUrl = comfyUiUrl ?? process.env.COMFYUI_URL ?? "http://localhost:8188";
  }

  async execute(input: AgentInput): Promise<AgentResult> {
    const startTime = Date.now();

    try {
      this.logExecution(input);
      const validated = ImageInputSchema.parse(input);

      this.logger.info("Image generation task received", {
        imageType: validated.context.image_type,
        style: validated.context.style,
        hasCharacterRef: !!validated.context.character_reference,
      });

      const result = await this.processImageTask(validated);
      const latency = Date.now() - startTime;

      return this.buildResult(result.prompt_used, {
        image_url: result.image_url,
        negative_prompt_used: result.negative_prompt_used,
        generation_time_ms: result.generation_time_ms,
        model_used: result.model_used,
        seed_used: result.seed_used,
      }, latency);
    } catch (error) {
      return this.handleError(error, input);
    }
  }

  private async processImageTask(input: z.infer<typeof ImageInputSchema>): Promise<z.infer<typeof ImageOutputSchema>> {
    const { text, context } = input;

    const prompt = this.buildPrompt(text, context);
    const negativePrompt = context.negative_prompt ?? this.getDefaultNegativePrompt();
    const seed = context.seed ?? Math.floor(Math.random() * 2147483647);

    try {
      const isAvailable = await this.checkComfyUiAvailability();
      if (!isAvailable) {
        throw new Error("ComfyUI service unavailable");
      }

      const genStartTime = Date.now();
      const imageUrl = await this.submitToComfyUi(prompt, negativePrompt, context, seed);
      const generationTime = Date.now() - genStartTime;

      return {
        image_url: imageUrl,
        prompt_used: prompt,
        negative_prompt_used: negativePrompt,
        generation_time_ms: generationTime,
        model_used: "comfyui-workflow",
        seed_used: seed,
      };
    } catch (error) {
      this.logger.error("Image generation failed", { error: String(error) });

      return {
        prompt_used: prompt,
        negative_prompt_used: negativePrompt,
        seed_used: seed,
        error: String(error),
      };
    }
  }

  private buildPrompt(text: string, context: z.infer<typeof ImageInputSchema>["context"]): string {
    const basePrompt = text;
    const styleSuffix = context.style ? `, ${context.style}` : "";
    const characterRef = context.character_reference ? `, character reference: ${context.character_reference}` : "";

    return `${basePrompt}${styleSuffix}${characterRef}, high quality, detailed`;
  }

  private getDefaultNegativePrompt(): string {
    return "low quality, blurry, deformed, ugly, bad anatomy, watermark, text, signature";
  }

  private async checkComfyUiAvailability(): Promise<boolean> {
    try {
      const response = await fetch(`${this.comfyUiUrl}/system_stats`);
      return response.ok;
    } catch {
      return false;
    }
  }

  private async submitToComfyUi(
    prompt: string,
    negativePrompt: string,
    context: z.infer<typeof ImageInputSchema>["context"],
    seed: number,
  ): Promise<string> {
    const workflow = this.buildComfyUiWorkflow(prompt, negativePrompt, context, seed);

    const response = await fetch(`${this.comfyUiUrl}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: workflow }),
    });

    if (!response.ok) {
      throw new Error(`ComfyUI returned ${response.status}`);
    }

    const data = (await response.json()) as { prompt_id: string };
    return `${this.comfyUiUrl}/view?prompt_id=${data.prompt_id}`;
  }

  private buildComfyUiWorkflow(
    prompt: string,
    negativePrompt: string,
    context: z.infer<typeof ImageInputSchema>["context"],
    seed: number,
  ): Record<string, unknown> {
    const width = context.dimensions?.width ?? 1024;
    const height = context.dimensions?.height ?? 1024;

    return {
      "3": {
        class_type: "KSampler",
        inputs: {
          seed,
          steps: 30,
          cfg: 7.0,
          sampler_name: "euler",
          scheduler: "normal",
          denoise: 1.0,
        },
      },
      "4": {
        class_type: "CheckpointLoaderSimple",
        inputs: { ckpt_name: "model.safetensors" },
      },
      "5": {
        class_type: "EmptyLatentImage",
        inputs: { width, height, batch_size: 1 },
      },
      "6": {
        class_type: "CLIPTextEncode",
        inputs: { text: prompt },
      },
      "7": {
        class_type: "CLIPTextEncode",
        inputs: { text: negativePrompt },
      },
    };
  }
}
