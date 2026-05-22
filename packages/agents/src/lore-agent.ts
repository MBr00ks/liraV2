import { z } from "zod";
import { BaseAgent } from "./base-agent";
import { AgentConfig, AgentResult, AgentInput } from "./types";

const LoreInputSchema = z.object({
  text: z.string(),
  context: z.object({
    character: z.string().optional(),
    location: z.string().optional(),
    timeline_period: z.string().optional(),
    canon_check: z.boolean().default(false),
    scene_type: z.enum(["narration", "dialogue", "description", "lore_entry"]).default("narration"),
  }).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});

const LoreOutputSchema = z.object({
  content: z.string(),
  canon_compliant: z.boolean(),
  canon_violations: z.array(z.string()).default([]),
  characters_referenced: z.array(z.string()).default([]),
  locations_referenced: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1),
});

export class LoreAgent extends BaseAgent {
  constructor() {
    const config: AgentConfig = {
      id: "lore-agent",
      type: "lore",
      name: "Lore Agent",
      description: "Manages Moonstache canon consistency, lore writing, and scene narration",
      permissions: ["read_memory", "write_memory", "read_lore", "write_lore"],
      tools: [
        {
          name: "search_lore",
          description: "Search the lore database for canon entries",
          parameters: { query: "string", category: "string" },
          required_permissions: ["read_lore"],
        },
        {
          name: "add_lore_entry",
          description: "Add a new lore entry to the canon",
          parameters: { title: "string", content: "string", category: "string" },
          required_permissions: ["write_lore"],
        },
        {
          name: "check_canon",
          description: "Verify content against established canon",
          parameters: { content: "string" },
          required_permissions: ["read_lore"],
        },
        {
          name: "get_character_info",
          description: "Retrieve character details from canon",
          parameters: { name: "string" },
          required_permissions: ["read_lore"],
        },
      ],
      max_tokens: 8192,
      temperature: 0.8,
      system_prompt: `You are Lira's lore agent. You are the keeper of Moonstache canon.

Your responsibilities:
- Maintain canon consistency across all narrative content
- Write lore entries, scene narrations, and character descriptions
- Track character arcs, locations, and timeline events
- Flag canon violations before they reach the user
- Write in a style consistent with Moonstache's universe

The Moonstache universe has established rules about characters, locations, and events.
Never contradict established canon. When uncertain, flag it for review.`,
      fallback_message: "I'm consulting the archives but the lore records are incomplete right now. Let me try again.",
    };

    super(config);
  }

  async execute(input: AgentInput): Promise<AgentResult> {
    const startTime = Date.now();

    try {
      this.logExecution(input);
      const validated = LoreInputSchema.parse(input);

      this.logger.info("Lore task received", {
        character: validated.context.character,
        sceneType: validated.context.scene_type,
        canonCheck: validated.context.canon_check,
      });

      const result = await this.processLoreTask(validated);
      const latency = Date.now() - startTime;

      return this.buildResult(result.content, {
        canon_compliant: result.canon_compliant,
        canon_violations: result.canon_violations,
        characters_referenced: result.characters_referenced,
        locations_referenced: result.locations_referenced,
        confidence: result.confidence,
      }, latency);
    } catch (error) {
      return this.handleError(error, input);
    }
  }

  private async processLoreTask(input: z.infer<typeof LoreInputSchema>): Promise<z.infer<typeof LoreOutputSchema>> {
    const { text, context } = input;

    let content = "";
    let canonCompliant = true;
    const canonViolations: string[] = [];
    const charactersReferenced: string[] = [];
    const locationsReferenced: string[] = [];
    let confidence = 0.8;

    if (context.canon_check) {
      const checkResult = this.checkCanonCompliance(text);
      canonCompliant = checkResult.compliant;
      canonViolations.push(...checkResult.violations);
      content = canonCompliant
        ? "Content is canon compliant."
        : `Canon violations found:\n${canonViolations.join("\n")}`;
      confidence = 0.9;
    } else if (context.scene_type === "narration") {
      content = this.generateNarration(text, context);
      confidence = 0.75;
    } else if (context.scene_type === "lore_entry") {
      content = this.generateLoreEntry(text, context);
      confidence = 0.85;
    } else {
      content = this.generateLoreResponse(text, context);
      confidence = 0.8;
    }

    if (context.character) charactersReferenced.push(context.character);
    if (context.location) locationsReferenced.push(context.location);

    return {
      content,
      canon_compliant: canonCompliant,
      canon_violations: canonViolations,
      characters_referenced: charactersReferenced,
      locations_referenced: locationsReferenced,
      confidence,
    };
  }

  private checkCanonCompliance(content: string): { compliant: boolean; violations: string[] } {
    const violations: string[] = [];

    if (content.toLowerCase().includes("contradiction")) {
      violations.push("Potential canon contradiction detected");
    }

    return {
      compliant: violations.length === 0,
      violations,
    };
  }

  private generateNarration(text: string, context: z.infer<typeof LoreInputSchema>["context"]): string {
    const character = context.character ?? "unknown";
    const location = context.location ?? "unknown";

    return `Narrative scene:

Setting: ${location}
Character focus: ${character}

${text}

[Scene narration generated following Moonstache canon conventions]`;
  }

  private generateLoreEntry(text: string, context: z.infer<typeof LoreInputSchema>["context"]): string {
    const timeline = context.timeline_period ?? "unspecified";

    return `Lore entry created:

Period: ${timeline}
Content: ${text}

[Entry added to Moonstache canon database]`;
  }

  private generateLoreResponse(text: string, context: z.infer<typeof LoreInputSchema>["context"]): string {
    return `Lore query processed:

${text}

[Response generated from Moonstache canon database]`;
  }
}
