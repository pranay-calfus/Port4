import { describe, expect, it, vi } from "vitest";
import { AIProvider } from "../src/ai/AIProvider";
import { routeTicket } from "../src/services/ticketRoutingService";
import { repairAndParse, extractFirstJsonObject, fixTrailingCommas, stripCodeFences } from "../src/services/jsonRepairService";
import { ticketRequestSchema } from "../src/validation/ticketRequestSchema";
import { AIUnavailableError, AIResponseError } from "../src/utils/AppError";
import { malformedResponses, validResponses } from "./fixtures/mockAIResponses";

describe("edge cases and JSON repair", () => {
  it("1. rejects empty input at the validation layer without ever calling the AI", () => {
    const result = ticketRequestSchema.safeParse({ message: "" });
    expect(result.success).toBe(false);
  });

  it("2. repairs a markdown code-fenced JSON string", () => {
    const parsed = repairAndParse(malformedResponses.codeFencedJson);
    expect(parsed).toMatchObject({ category: "Billing" });
  });

  it("3. repairs a JSON string with a trailing comma", () => {
    const parsed = repairAndParse(malformedResponses.trailingComma);
    expect(parsed).toMatchObject({ category: "Billing" });
  });

  it("4. extracts a JSON object wrapped in prose", () => {
    const parsed = repairAndParse(malformedResponses.proseWrapped);
    expect(parsed).toMatchObject({ category: "Billing" });
  });

  it("4b. repair helper functions behave correctly in isolation", () => {
    expect(stripCodeFences("```json\n{\"a\":1}\n```")).toBe('{"a":1}');
    expect(fixTrailingCommas('{"a":1,}')).toBe('{"a":1}');
    expect(extractFirstJsonObject('prefix {"a":1} suffix')).toBe('{"a":1}');
  });

  it("5. retries once and succeeds when the second AI call returns a valid response", async () => {
    const mockProvider: AIProvider = {
      routeTicket: vi
        .fn()
        .mockResolvedValueOnce(malformedResponses.invalidCategory)
        .mockResolvedValueOnce(validResponses[0])
    };

    const result = await routeTicket("some ticket text", mockProvider);
    expect(result.category).toBe("Billing");
    expect(mockProvider.routeTicket).toHaveBeenCalledTimes(2);
  });

  it("6. throws AIResponseError when both attempts return invalid data", async () => {
    const mockProvider: AIProvider = {
      routeTicket: vi
        .fn()
        .mockResolvedValueOnce(malformedResponses.invalidCategory)
        .mockResolvedValueOnce(malformedResponses.confidenceOutOfRange)
    };

    await expect(routeTicket("some ticket text", mockProvider)).rejects.toBeInstanceOf(AIResponseError);
    expect(mockProvider.routeTicket).toHaveBeenCalledTimes(2);
  });

  it("7. surfaces AIUnavailableError when the provider itself fails (e.g. missing API key)", async () => {
    const mockProvider: AIProvider = {
      routeTicket: vi.fn().mockRejectedValue(new AIUnavailableError("AI service unavailable: missing API key"))
    };

    await expect(routeTicket("some ticket text", mockProvider)).rejects.toBeInstanceOf(AIUnavailableError);
  });

  it("8. succeeds on the first attempt without retrying when the response is already valid", async () => {
    const mockProvider: AIProvider = {
      routeTicket: vi.fn().mockResolvedValueOnce(validResponses[1])
    };

    const result = await routeTicket("some ticket text", mockProvider);
    expect(result.category).toBe("Technical Support");
    expect(mockProvider.routeTicket).toHaveBeenCalledTimes(1);
  });
});
