import { config } from "./config/env";
import { createApp } from "./app";
import { logger } from "./utils/logger";

const app = createApp();

app.listen(config.PORT, () => {
  logger.info(`Smart Ticket Router backend listening on port ${config.PORT}`, {
    aiProvider: "groq",
    model: config.GROQ_MODEL
  });
});

export default app;
