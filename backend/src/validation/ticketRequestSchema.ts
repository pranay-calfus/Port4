import { z } from "zod";

// Hard cap on ticket length. Anything longer is truncated (not rejected)
// before being sent to the AI - see services/promptService.ts.
export const MAX_TICKET_LENGTH = 8000;

export const ticketRequestSchema = z.object({
  message: z
    .string({ required_error: "message is required", invalid_type_error: "message must be a string" })
    .trim()
    .min(1, "message cannot be empty")
});

export type TicketRequestInput = z.infer<typeof ticketRequestSchema>;
