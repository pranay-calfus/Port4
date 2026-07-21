import type {
  AdminSummary,
  AdminTicketFilters,
  ChatMessageResponse,
  ChatTurn,
  DashboardMetrics,
  Priority,
  TicketDetailOut,
  TicketOut,
  TokenResponse,
  UserOut,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

async function request<T>(
  method: string,
  path: string,
  options: { token?: string | null; body?: unknown; query?: Record<string, string | number | undefined> } = {}
): Promise<T> {
  const { token, body, query } = options;

  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(503, `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`);
  }

  if (response.status === 401) {
    unauthorizedHandler?.();
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data?.detail ?? detail;
    } catch {
      // body wasn't JSON, fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}

// --- Auth ---

export function register(name: string, email: string, password: string) {
  return request<TokenResponse>("POST", "/auth/register", { body: { name, email, password } });
}

export function login(email: string, password: string) {
  return request<TokenResponse>("POST", "/auth/login", { body: { email, password } });
}

export function adminLogin(email: string, password: string) {
  return request<TokenResponse>("POST", "/admin/login", { body: { email, password } });
}

export function whoami(token: string) {
  return request<TokenResponse["user"]>("GET", "/auth/me", { token });
}

export function forgotPassword(email: string) {
  return request<{ message: string }>("POST", "/auth/forgot-password", { body: { email } });
}

// --- Chat / escalation ---

export function sendChatMessage(token: string, message: string, history: ChatTurn[]) {
  return request<ChatMessageResponse>("POST", "/chat/message", { token, body: { message, history } });
}

export function escalateChat(token: string, history: ChatTurn[], priority?: Priority) {
  return request<TicketDetailOut>("POST", "/chat/escalate", { token, body: { history, priority } });
}

// --- Customer tickets ---

export function listMyTickets(token: string) {
  return request<TicketOut[]>("GET", "/tickets", { token });
}

export function getMyTicket(token: string, ticketId: number) {
  return request<TicketDetailOut>("GET", `/tickets/${ticketId}`, { token });
}

export function replyToTicket(token: string, ticketId: number, message: string) {
  return request<TicketDetailOut>("POST", `/tickets/${ticketId}/messages`, { token, body: { message } });
}

export function acceptSolution(token: string, ticketId: number) {
  return request<TicketOut>("POST", `/tickets/${ticketId}/accept-solution`, { token });
}

export function reopenTicket(token: string, ticketId: number) {
  return request<TicketOut>("POST", `/tickets/${ticketId}/reopen`, { token });
}

export function updateTicketPriority(token: string, ticketId: number, priority: string) {
  return request<TicketOut>("PATCH", `/tickets/${ticketId}/priority`, { token, body: { priority } });
}

// --- Admin ---

export function adminListTickets(token: string, filters: AdminTicketFilters = {}) {
  return request<TicketOut[]>("GET", "/admin/tickets", { token, query: filters });
}

export function adminGetTicket(token: string, ticketId: number) {
  return request<TicketDetailOut>("GET", `/admin/tickets/${ticketId}`, { token });
}

export function adminUpdateStatus(token: string, ticketId: number, status: string) {
  return request<TicketOut>("PATCH", `/admin/tickets/${ticketId}/status`, { token, body: { status } });
}

export function adminAssign(token: string, ticketId: number, adminId: number) {
  return request<TicketOut>("PATCH", `/admin/tickets/${ticketId}/assign`, {
    token,
    body: { admin_id: adminId },
  });
}

export function adminReassign(
  token: string,
  ticketId: number,
  department?: string,
  priority?: string
) {
  return request<TicketOut>("PATCH", `/admin/tickets/${ticketId}/reassign`, {
    token,
    body: { department, priority },
  });
}

export function adminDeleteTicket(token: string, ticketId: number) {
  return request<null>("DELETE", `/admin/tickets/${ticketId}`, { token });
}

export function adminReply(token: string, ticketId: number, message: string) {
  return request<TicketDetailOut>("POST", `/admin/tickets/${ticketId}/message`, {
    token,
    body: { message },
  });
}

export function adminMetrics(token: string, dateRange: { date_from?: string; date_to?: string } = {}) {
  return request<DashboardMetrics>("GET", "/admin/metrics", { token, query: dateRange });
}

export function adminListAdmins(token: string) {
  return request<AdminSummary[]>("GET", "/admin/admins", { token });
}

export function adminCreateAdmin(
  token: string,
  name: string,
  email: string,
  password: string,
  department?: string
) {
  return request<UserOut>("POST", "/admin/admins", {
    token,
    body: { name, email, password, department: department || null },
  });
}

export function adminDeleteAdmin(token: string, adminId: number) {
  return request<null>("DELETE", `/admin/admins/${adminId}`, { token });
}
