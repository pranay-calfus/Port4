import { NextFunction, Request, Response } from "express";

export function timing(req: Request, _res: Response, next: NextFunction): void {
  req.startTime = process.hrtime.bigint();
  next();
}

export function getElapsedMs(req: Request): number {
  if (!req.startTime) return 0;
  const elapsedNs = process.hrtime.bigint() - req.startTime;
  return Number(elapsedNs / BigInt(1_000_000));
}
