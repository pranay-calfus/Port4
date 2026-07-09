import axios, { AxiosError } from "axios";
import { ApiErrorResponse, ApiSuccessResponse } from "../types/ticket";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000/api",
  timeout: 30000
});

export async function routeTicket(message: string): Promise<ApiSuccessResponse> {
  const { data } = await client.post<ApiSuccessResponse>("/route-ticket", { message });
  return data;
}

/**
 * Normalizes any error thrown by routeTicket() into a user-facing message,
 * preferring the structured error body the backend returns.
 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorResponse>;
    const backendMessage = axiosError.response?.data?.error?.message;
    if (backendMessage) return backendMessage;
    if (axiosError.code === "ECONNABORTED") return "The request timed out. Please try again.";
    if (!axiosError.response) return "Could not reach the server. Is the backend running?";
    return axiosError.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
