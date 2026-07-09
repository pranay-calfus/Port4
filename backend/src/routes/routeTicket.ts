import { Request, Response } from "express";
import { routeTicket as routeTicketService } from "../services/ticketRoutingService";
import { asyncHandler } from "../utils/asyncHandler";
import { getElapsedMs } from "../middleware/timing";
import { ticketRequestSchema } from "../validation/ticketRequestSchema";
import { ApiSuccessResponse } from "../types/ticket";
import type { TicketRouteResult } from "../types/ticket";

export const routeTicketHandler = asyncHandler(async (req: Request, res: Response) => {
  const { message } = ticketRequestSchema.parse(req.body);

  const data = await routeTicketService(message);

  const response: ApiSuccessResponse<TicketRouteResult> = {
    success: true,
    data,
    processingTime: `${getElapsedMs(req)} ms`
  };

  res.status(200).json(response);
});
