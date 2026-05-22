import { z } from "zod";
import { BaseAgent } from "./base-agent";
import { AgentConfig, AgentResult, AgentInput } from "./types";

const ResearchInputSchema = z.object({
  text: z.string(),
  context: z.object({
    search_type: z.enum(["web", "technical", "cosplay_reference", "general"]).default("general"),
    max_results: z.number().default(5),
    depth: z.enum(["shallow", "deep"]).default("shallow"),
    previous_findings: z.array(z.string()).default([]),
  }).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});

const ResearchOutputSchema = z.object({
  summary: z.string(),
  findings: z.array(z.object({
    title: z.string(),
    content: z.string(),
    source: z.string().optional(),
    relevance: z.number().min(0).max(1),
  })).default([]),
  follow_up_queries: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1),
});

export class ResearchAgent extends BaseAgent {
  constructor() {
    const config: AgentConfig = {
      id: "research-agent",
      type: "research",
      name: "Research Agent",
      description: "Handles web research, cosplay design references, and technical research",
      permissions: ["read_memory", "write_memory", "web_search"],
      tools: [
        {
          name: "web_search",
          description: "Perform a web search query",
          parameters: { query: "string", num_results: "number" },
          required_permissions: ["web_search"],
        },
        {
          name: "fetch_url",
          description: "Fetch and parse content from a URL",
          parameters: { url: "string" },
          required_permissions: ["web_search"],
        },
        {
          name: "summarize_findings",
          description: "Summarize research findings",
          parameters: { findings: "array" },
          required_permissions: ["read_memory"],
        },
      ],
      max_tokens: 4096,
      temperature: 0.5,
      system_prompt: `You are Lira's research agent. You specialize in:
- Web research and information gathering
- Cosplay design references and material sourcing
- Technical research for development tasks
- Image and visual reference gathering

Provide well-sourced, organized findings. Always cite sources when possible.
For cosplay research, focus on accuracy of materials, patterns, and visual references.
For technical research, provide actionable information with version numbers and documentation links.`,
      fallback_message: "I'm having trouble gathering research right now. The search systems may be temporarily unavailable.",
    };

    super(config);
  }

  async execute(input: AgentInput): Promise<AgentResult> {
    const startTime = Date.now();

    try {
      this.logExecution(input);
      const validated = ResearchInputSchema.parse(input);

      this.logger.info("Research task received", {
        searchType: validated.context.search_type,
        depth: validated.context.depth,
        maxResults: validated.context.max_results,
      });

      const result = await this.processResearchTask(validated);
      const latency = Date.now() - startTime;

      return this.buildResult(result.summary, {
        findings: result.findings,
        follow_up_queries: result.follow_up_queries,
        confidence: result.confidence,
      }, latency);
    } catch (error) {
      return this.handleError(error, input);
    }
  }

  private async processResearchTask(input: z.infer<typeof ResearchInputSchema>): Promise<z.infer<typeof ResearchOutputSchema>> {
    const { text, context } = input;

    let summary = "";
    const findings: z.infer<typeof ResearchOutputSchema>["findings"] = [];
    const followUpQueries: string[] = [];
    let confidence = 0.6;

    switch (context.search_type) {
      case "web":
        summary = this.generateWebSearchSummary(text, context);
        confidence = 0.7;
        break;
      case "technical":
        summary = this.generateTechnicalSummary(text, context);
        confidence = 0.8;
        break;
      case "cosplay_reference":
        summary = this.generateCosplaySummary(text, context);
        confidence = 0.75;
        break;
      default:
        summary = this.generateGeneralSummary(text, context);
        confidence = 0.65;
    }

    followUpQueries.push(`Refine: ${text}`);

    return { summary, findings, follow_up_queries: followUpQueries, confidence };
  }

  private generateWebSearchSummary(query: string, context: z.infer<typeof ResearchInputSchema>["context"]): string {
    return `Web research for: "${query}"

Search depth: ${context.depth}
Max results: ${context.max_results}

[Web search results would be gathered and summarized here]

Sources would be cited for each finding.`;
  }

  private generateTechnicalSummary(query: string, context: z.infer<typeof ResearchInputSchema>["context"]): string {
    return `Technical research for: "${query}"

[Technical documentation, API references, and best practices would be compiled]

Focus areas:
- Current version compatibility
- Implementation patterns
- Known issues and workarounds
- Community recommendations`;
  }

  private generateCosplaySummary(query: string, context: z.infer<typeof ResearchInputSchema>["context"]): string {
    return `Cosplay reference research for: "${query}"

[Visual references, material lists, and construction guides would be compiled]

Research areas:
- Character reference images
- Material and fabric recommendations
- Construction techniques
- Accessory and prop details`;
  }

  private generateGeneralSummary(query: string, context: z.infer<typeof ResearchInputSchema>["context"]): string {
    return `General research for: "${query}"

[General information gathering and synthesis]

Previous findings considered: ${context.previous_findings.length} entries`;
  }
}
