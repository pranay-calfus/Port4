import cors from "cors";
import express from "express";
import { errorHandler } from "./middleware/errorHandler";
import { notFoundHandler } from "./middleware/notFoundHandler";
import { timing } from "./middleware/timing";
import router from "./routes";

/**
 * Builds the Express app without starting a listener, so it can be
 * imported directly in tests (via supertest) as well as by server.ts.
 */
export function createApp() {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: "1mb" }));
  app.use(timing);

  app.use("/api", router);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
