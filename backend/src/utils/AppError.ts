export class AppError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: unknown;

  constructor(message: string, statusCode: number, code: string, details?: unknown) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: unknown) {
    super(message, 400, "VALIDATION_ERROR", details);
  }
}

export class AIUnavailableError extends AppError {
  constructor(message: string, details?: unknown) {
    super(message, 500, "AI_UNAVAILABLE", details);
  }
}

export class AIResponseError extends AppError {
  constructor(message: string, details?: unknown) {
    super(message, 500, "AI_RESPONSE_ERROR", details);
  }
}
