import { z } from "zod";
import { ASSIGNED_TEAMS, CATEGORIES, PRIORITIES } from "../types/ticket";

// This mirrors the AI output contract exactly. It is the second line of
// defense after the Groq tool's own parameters schema (see ai/GroqProvider.ts) -
// it guards against enum drift, wrong types, or a malformed tool call.
export const ticketResultSchema = z.object({
  category: z.enum(CATEGORIES),
  priority: z.enum(PRIORITIES),
  assignedTeam: z.enum(ASSIGNED_TEAMS),
  reasoning: z.string().min(1, "reasoning cannot be empty"),
  confidence: z.number().min(0).max(1)
});

export type TicketResultInput = z.infer<typeof ticketResultSchema>;
