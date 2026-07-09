import { AIProvider } from "../ai/AIProvider";
import { GroqProvider } from "../ai/GroqProvider";
import { TicketRouteResult } from "../types/ticket";
import { AIResponseError } from "../utils/AppError";
import { logger } from "../utils/logger";
import { repairAndParse } from "./jsonRepairService";
import { summarizeValidationError, truncateMessage } from "./promptService";
import { ticketResultSchema } from "../validation/ticketResultSchema";

/**
 * Attempts to coerce a raw provider output into a validated
 * TicketRouteResult. Tries the value as-is first (the common case, since
 * forced tool-use already returns a parsed object), then falls back to
 * string-based JSON repair if the value isn't already a plain object.
 */
function validateOrRepair(raw: unknown): TicketRouteResult | { error: string } {
  const directAttempt = ticketResultSchema.safeParse(raw);
  if (directAttempt.success) {
    return directAttempt.data;
  }

  if (typeof raw === "string") {
    const repaired = repairAndParse(raw);
    if (repaired !== null) {
      const repairedAttempt = ticketResultSchema.safeParse(repaired);
      if (repairedAttempt.success) {
        return repairedAttempt.data;
      }
      return { error: summarizeValidationError(repairedAttempt.error) };
    }
  }

  return { error: summarizeValidationError(directAttempt.error) };
}

/**
 * Orchestrates the full JSON-reliability pipeline for a single ticket:
 *   1. Call the AI provider.
 *   2. Validate (with a repair fallback) against the strict schema.
 *   3. On failure, retry the AI call exactly once with the error appended
 *      as context, then validate/repair again.
 *   4. On persistent failure, throw a typed AppError - never an unhandled
 *      exception.
 */
export async function routeTicket(
  message: string,
  provider: AIProvider = new GroqProvider()
): Promise<TicketRouteResult> {
  const { text, truncated } = truncateMessage(message);
  if (truncated) {
    logger.warn("Ticket message truncated before sending to AI", { originalLength: message.length });
  }

  const firstRaw = await provider.routeTicket(text);
  const firstResult = validateOrRepair(firstRaw);

  if (!("error" in firstResult)) {
    return firstResult;
  }

  logger.warn("Initial AI response failed validation, retrying once", { error: firstResult.error });

  const secondRaw = await provider.routeTicket(text, { retryContext: firstResult.error });
  const secondResult = validateOrRepair(secondRaw);

  if (!("error" in secondResult)) {
    return secondResult;
  }

  logger.error("AI response failed validation after retry", { error: secondResult.error });
  throw new AIResponseError(
    "The AI service could not produce a valid response after retries.",
    { lastError: secondResult.error }
  );
}
