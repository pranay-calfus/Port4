import { describe, expect, it } from "vitest";
import { ticketResultSchema } from "../src/validation/ticketResultSchema";
import { malformedResponses, validResponses } from "./fixtures/mockAIResponses";

describe("ticketResultSchema - 10 consecutive JSON validation tests", () => {
  it("1. validates a Billing response with all required fields", () => {
    const result = ticketResultSchema.safeParse(validResponses[0]);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(Object.keys(result.data)).toEqual(
        expect.arrayContaining(["category", "priority", "assignedTeam", "reasoning", "confidence"])
      );
    }
  });

  it("2. validates a Technical Support response", () => {
    expect(ticketResultSchema.safeParse(validResponses[1]).success).toBe(true);
  });

  it("3. validates a Security response with High priority", () => {
    const result = ticketResultSchema.safeParse(validResponses[2]);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.priority).toBe("High");
  });

  it("4. validates a Feature Request response with Low priority", () => {
    const result = ticketResultSchema.safeParse(validResponses[3]);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.priority).toBe("Low");
  });

  it("5. rejects a response missing the reasoning field", () => {
    const result = ticketResultSchema.safeParse(malformedResponses.missingField);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((issue) => issue.path.includes("reasoning"))).toBe(true);
    }
  });

  it("6. rejects a response with an invalid category enum value", () => {
    const result = ticketResultSchema.safeParse(malformedResponses.invalidCategory);
    expect(result.success).toBe(false);
  });

  it("7. rejects a response with confidence out of range", () => {
    const result = ticketResultSchema.safeParse(malformedResponses.confidenceOutOfRange);
    expect(result.success).toBe(false);
  });

  it("8. rejects a response with confidence as a string instead of a number", () => {
    const result = ticketResultSchema.safeParse(malformedResponses.confidenceAsString);
    expect(result.success).toBe(false);
  });

  it("9. strips unexpected extra fields but still validates known-good data", () => {
    const result = ticketResultSchema.safeParse({ ...validResponses[4], extraField: "ignore me" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect((result.data as Record<string, unknown>).extraField).toBeUndefined();
    }
  });

  it("10. validates all remaining sample AI responses successfully with no missing fields", () => {
    for (const response of validResponses.slice(4)) {
      const result = ticketResultSchema.safeParse(response);
      expect(result.success).toBe(true);
    }
  });
});
