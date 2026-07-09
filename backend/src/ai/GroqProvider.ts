import OpenAI from "openai";
import { config } from "../config/env";
import { SYSTEM_PROMPT } from "../prompts/systemPrompt";
import { ASSIGNED_TEAMS, CATEGORIES, PRIORITIES } from "../types/ticket";
import { AIUnavailableError, AIResponseError } from "../utils/AppError";
import { logger } from "../utils/logger";
import { AIProvider, RouteTicketOptions } from "./AIProvider";

const GROQ_BASE_URL = "https://api.groq.com/openai/v1";
const ROUTE_TICKET_TOOL_NAME = "route_ticket";

// Forcing the model to call this tool is our primary structured-output
// guarantee (Layer 2 of JSON reliability, see docs/AI-Concepts.md). Groq
// exposes an OpenAI-compatible Chat Completions API, so we use the same
// function-calling mechanism the OpenAI SDK provides.
const routeTicketTool: OpenAI.Chat.Completions.ChatCompletionTool = {
  type: "function",
  function: {
    name: ROUTE_TICKET_TOOL_NAME,
    description: "Classify a support ticket and return the routing decision.",
    parameters: {
      type: "object",
      properties: {
        category: { type: "string", enum: [...CATEGORIES] },
        priority: { type: "string", enum: [...PRIORITIES] },
        assignedTeam: { type: "string", enum: [...ASSIGNED_TEAMS] },
        reasoning: {
          type: "string",
          description: "One sentence justifying the decision, citing a specific signal from the ticket."
        },
        confidence: { type: "number", description: "A number between 0 and 1." }
      },
      required: ["category", "priority", "assignedTeam", "reasoning", "confidence"],
      additionalProperties: false
    }
  }
};

export class GroqProvider implements AIProvider {
  private client: OpenAI | null = null;

  private getClient(): OpenAI {
    if (!config.GROQ_API_KEY) {
      throw new AIUnavailableError(
        "AI service unavailable: GROQ_API_KEY is not configured. Set it in backend/.env."
      );
    }
    if (!this.client) {
      this.client = new OpenAI({ apiKey: config.GROQ_API_KEY, baseURL: GROQ_BASE_URL });
    }
    return this.client;
  }

  async routeTicket(userMessage: string, options?: RouteTicketOptions): Promise<unknown> {
    const client = this.getClient();

    const userContent = options?.retryContext
      ? `${userMessage}\n\n[SYSTEM NOTICE] Your previous response failed validation: ${options.retryContext}. Re-emit strictly valid arguments via the ${ROUTE_TICKET_TOOL_NAME} tool only.`
      : userMessage;

    let response: OpenAI.Chat.Completions.ChatCompletion;
    try {
      response = await client.chat.completions.create({
        model: config.GROQ_MODEL,
        max_tokens: 1024,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userContent }
        ],
        tools: [routeTicketTool],
        tool_choice: { type: "function", function: { name: ROUTE_TICKET_TOOL_NAME } }
      });
    } catch (error) {
      logger.error("Groq API call failed", { error: (error as Error).message });
      throw new AIUnavailableError("AI service is currently unavailable.", {
        cause: (error as Error).message
      });
    }

    const toolCall = response.choices[0]?.message?.tool_calls?.[0];

    if (!toolCall || toolCall.type !== "function") {
      throw new AIResponseError("The AI response did not include a structured tool call.");
    }

    return toolCall.function.arguments;
  }
}
