import { useState } from "react";
import { extractErrorMessage, routeTicket } from "../services/api";
import { ApiSuccessResponse } from "../types/ticket";

export function useRouteTicket() {
  const [data, setData] = useState<ApiSuccessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(message: string): Promise<ApiSuccessResponse | null> {
    setLoading(true);
    setError(null);
    try {
      const result = await routeTicket(message);
      setData(result);
      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setData(null);
    setError(null);
  }

  return { data, loading, error, submit, clear };
}
