import { NextFunction, Request, Response } from "express";
import { ZodError } from "zod";
import { AppError, ValidationError } from "../utils/AppError";
import { logger } from "../utils/logger";

/**
 * Final backstop for the "backend never crashes" requirement. Every error
 * that reaches here (typed AppError, ZodError, or an unexpected exception)
 * is converted into a safe JSON error response - the stack is logged, but
 * never leaked to the client.
 */
export function errorHandler(err: unknown, _req: Request, res: Response, _next: NextFunction): void {
  if (err instanceof ZodError) {
    const validationError = new ValidationError("Invalid request payload.", err.flatten());
    res.status(validationError.statusCode).json({
      success: false,
      error: { message: validationError.message, code: validationError.code, details: validationError.details }
    });
    return;
  }

  if (err instanceof AppError) {
    logger.warn("Handled application error", { code: err.code, message: err.message });
    res.status(err.statusCode).json({
      success: false,
      error: { message: err.message, code: err.code, details: err.details }
    });
    return;
  }

  logger.error("Unexpected error", { error: err instanceof Error ? err.stack : String(err) });
  res.status(500).json({
    success: false,
    error: { message: "An unexpected server error occurred.", code: "INTERNAL_ERROR" }
  });
}
