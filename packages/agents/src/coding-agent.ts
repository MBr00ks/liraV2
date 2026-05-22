import { z } from "zod";
import { BaseAgent } from "./base-agent";
import { AgentConfig, AgentResult, AgentInput } from "./types";

const CodingInputSchema = z.object({
  text: z.string(),
  context: z.object({
    file_path: z.string().optional(),
    language: z.string().optional(),
    error_message: z.string().optional(),
    code_snippet: z.string().optional(),
  }).default({}),
  priority: z.enum(["low", "normal", "high"]).default("normal"),
  session_id: z.string().optional(),
});

const CodingOutputSchema = z.object({
  solution: z.string(),
  explanation: z.string(),
  code_changes: z.array(z.object({
    file: z.string(),
    action: z.enum(["create", "update", "delete"]),
    content: z.string().optional(),
  })).default([]),
  confidence: z.number().min(0).max(1),
});

export class CodingAgent extends BaseAgent {
  constructor() {
    const config: AgentConfig = {
      id: "coding-agent",
      type: "coding",
      name: "Coding Agent",
      description: "Handles coding, architecture, technical planning, and debugging tasks",
      permissions: ["read_memory", "write_memory", "file_read", "file_write", "code_execution", "shell_command"],
      tools: [
        {
          name: "read_file",
          description: "Read file contents from the project",
          parameters: { path: "string" },
          required_permissions: ["file_read"],
        },
        {
          name: "write_file",
          description: "Write or update a file in the project",
          parameters: { path: "string", content: "string" },
          required_permissions: ["file_write"],
        },
        {
          name: "run_command",
          description: "Execute a shell command",
          parameters: { command: "string", cwd: "string" },
          required_permissions: ["shell_command"],
        },
        {
          name: "search_codebase",
          description: "Search the codebase for patterns",
          parameters: { pattern: "string", path: "string" },
          required_permissions: ["file_read"],
        },
      ],
      max_tokens: 8192,
      temperature: 0.3,
      system_prompt: `You are Lira's coding agent. You specialize in:
- TypeScript and Python development
- Architecture design and technical planning
- Debugging and troubleshooting
- Code review and refactoring
- Build system and dependency management

Follow the project's coding standards strictly. Always explain your reasoning.
When debugging, provide step-by-step analysis. When writing code, follow existing patterns.`,
      fallback_message: "I'm having trouble analyzing the code right now. Please try again or provide more context.",
    };

    super(config);
  }

  async execute(input: AgentInput): Promise<AgentResult> {
    const startTime = Date.now();

    try {
      this.logExecution(input);
      const validated = CodingInputSchema.parse(input);

      this.logger.info("Coding task received", {
        language: validated.context.language,
        hasError: !!validated.context.error_message,
        hasCodeSnippet: !!validated.context.code_snippet,
      });

      const result = await this.processCodingTask(validated);
      const latency = Date.now() - startTime;

      return this.buildResult(result.solution, {
        explanation: result.explanation,
        code_changes: result.code_changes,
        confidence: result.confidence,
      }, latency);
    } catch (error) {
      return this.handleError(error, input);
    }
  }

  private async processCodingTask(input: z.infer<typeof CodingInputSchema>): Promise<z.infer<typeof CodingOutputSchema>> {
    const { text, context } = input;

    let solution = "";
    let explanation = "";
    const codeChanges: z.infer<typeof CodingOutputSchema>["code_changes"] = [];
    let confidence = 0.7;

    if (context.error_message) {
      explanation = `Analyzing error: ${context.error_message}`;
      solution = this.generateDebugResponse(text, context);
      confidence = 0.8;
    } else if (context.code_snippet) {
      explanation = "Reviewing and improving the provided code";
      solution = this.generateCodeReviewResponse(text, context);
      confidence = 0.85;
    } else {
      explanation = "Processing coding request";
      solution = this.generateCodingResponse(text);
      confidence = 0.75;
    }

    return { solution, explanation, code_changes: codeChanges, confidence };
  }

  private generateDebugResponse(request: string, context: NonNullable<AgentInput["context"]>): string {
    const errorMessage = context.error_message ?? "Unknown error";
    const filePath = context.file_path ?? "unknown file";

    return `Debugging analysis for ${filePath}:

Error: ${errorMessage}

Steps to resolve:
1. Identify the root cause from the error message
2. Check the surrounding code for context
3. Apply the fix following project conventions
4. Verify the fix doesn't break related functionality

Request: ${request}`;
  }

  private generateCodeReviewResponse(request: string, context: NonNullable<AgentInput["context"]>): string {
    const snippet = context.code_snippet ?? "";

    return `Code review:

${snippet}

Review notes:
- Check for type safety and strict mode compliance
- Verify error handling is explicit and recoverable
- Ensure naming follows project conventions
- Look for opportunities to extract reusable logic

Request: ${request}`;
  }

  private generateCodingResponse(request: string): string {
    return `Processing coding request:

${request}

I will analyze the requirements and provide a solution following the project's architecture patterns and coding standards.`;
  }
}
