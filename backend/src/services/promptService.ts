import { MAX_TICKET_LENGTH } from "../validation/ticketRequestSchema";

export interface TruncationResult {
  text: string;
  truncated: boolean;
}

/**
 * Enforces the documented input-length limit before sending a ticket to the
 * AI. Truncation (not rejection) keeps huge inputs usable - see the "huge
 * input" edge case in docs/AI-Concepts.md.
 */
export function truncateMessage(message: string): TruncationResult {
  if (message.length <= MAX_TICKET_LENGTH) {
    return { text: message, truncated: false };
  }
  return { text: message.slice(0, MAX_TICKET_LENGTH), truncated: true };
}

/**
 * Builds a concise, human-readable summary of a Zod/parse failure to hand
 * back to the AI provider as retry context.
 */
export function summarizeValidationError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "the response could not be parsed as valid structured output";
}
