import dotenv from "dotenv";
import { z } from "zod";

dotenv.config();

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(5000),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  // Optional here so the server can still boot without a key configured.
  // A missing key is only surfaced when a request actually needs the AI
  // provider, as a clean 500 error - see ai/GroqProvider.ts.
  GROQ_API_KEY: z.string().optional(),
  GROQ_MODEL: z.string().default("llama-3.3-70b-versatile")
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  // Env shape itself is malformed (e.g. PORT is not a number) - this is a
  // startup-time configuration bug, not a runtime AI failure, so failing
  // fast here is correct.
  console.error("Invalid environment configuration:", parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const config = parsed.data;
