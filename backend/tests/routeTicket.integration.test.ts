import request from "supertest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { validResponses } from "./fixtures/mockAIResponses";

const routeTicketMock = vi.fn();

vi.mock("../src/ai/GroqProvider", () => ({
  GroqProvider: vi.fn().mockImplementation(() => ({ routeTicket: routeTicketMock }))
}));

describe("POST /api/route-ticket (integration)", () => {
  beforeEach(() => {
    routeTicketMock.mockReset();
  });

  it("returns 400 for an empty message body", async () => {
    const { createApp } = await import("../src/app");
    const app = createApp();

    const res = await request(app).post("/api/route-ticket").send({ message: "" });

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(routeTicketMock).not.toHaveBeenCalled();
  });

  it("returns 200 with valid data and a processingTime string on success", async () => {
    routeTicketMock.mockResolvedValueOnce(validResponses[0]);
    const { createApp } = await import("../src/app");
    const app = createApp();

    const res = await request(app)
      .post("/api/route-ticket")
      .send({ message: "I was charged twice for my subscription." });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.category).toBe("Billing");
    expect(res.body.processingTime).toMatch(/\d+ ms/);
  });

  it("returns 500 with a clear error body when the AI is unavailable", async () => {
    routeTicketMock.mockRejectedValue(new Error("network error"));
    const { createApp } = await import("../src/app");
    const app = createApp();

    const res = await request(app).post("/api/route-ticket").send({ message: "help me please" });

    expect(res.status).toBe(500);
    expect(res.body.success).toBe(false);
    expect(res.body.error.message).toBeDefined();
  });
});
