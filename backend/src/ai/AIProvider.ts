export interface RouteTicketOptions {
  /**
   * When set, this is the single automatic retry: the previous attempt's
   * error is appended to the prompt so the model can self-correct.
   */
  retryContext?: string;
}

/**
 * Abstraction implemented by GroqProvider (the app's only AI provider).
 * Keeping this as an interface - rather than calling GroqProvider directly
 * everywhere - is what lets tests inject a fake provider instead of making
 * real network calls.
 */
export interface AIProvider {
  /**
   * Returns the raw, not-yet-validated structured output from the model.
   * Validation is owned by services/ticketRoutingService.ts, not the provider.
   */
  routeTicket(userMessage: string, options?: RouteTicketOptions): Promise<unknown>;
}
