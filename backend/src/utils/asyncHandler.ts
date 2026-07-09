import { NextFunction, Request, Response } from "express";

type AsyncRouteHandler = (req: Request, res: Response, next: NextFunction) => Promise<unknown>;

/**
 * Wraps an async route/middleware handler so any rejected promise is
 * forwarded to Express's error-handling chain instead of crashing the
 * process. This is the routing-layer half of the "backend never crashes"
 * guarantee.
 */
export function asyncHandler(fn: AsyncRouteHandler) {
  return (req: Request, res: Response, next: NextFunction): void => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}
