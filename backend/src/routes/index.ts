import { Router } from "express";
import { routeTicketHandler } from "./routeTicket";

const router = Router();

router.get("/health", (_req, res) => {
  res.status(200).json({ success: true, data: { status: "ok" } });
});

router.post("/route-ticket", routeTicketHandler);

export default router;
