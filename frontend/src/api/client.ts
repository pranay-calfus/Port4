import type {
  AdminSummary,
  AdminTicketFilters,
  AnswerValue,
  ChatMessageResponse,
  ChatTurn,
  DashboardMetrics,
  EscalateResponse,
  FeedbackDetailOut,
  FeedbackFilters,
  FeedbackMetrics,
  FeedbackOut,
  Priority,
  Role,
  Survey,
  SurveyAnalytics,
  SurveyDetail,
  SurveyQuestionInput,
  SurveyResponse,
  SurveyResponseFilters,
  TeamAccountSummary,
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

export function productCxLogin(email: string, password: string) {
  return request<TokenResponse>("POST", "/product-cx/login", { body: { email, password } });
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
  return request<EscalateResponse>("POST", "/chat/escalate", { token, body: { history, priority } });
}

export function bulkCreateTickets(token: string, messages: string[]) {
  return request<EscalateResponse[]>("POST", "/tickets/bulk", { token, body: { messages } });
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
  department?: string,
  role: Role = "ADMIN"
) {
  return request<UserOut>("POST", "/admin/admins", {
    token,
    body: { name, email, password, department: department || null, role },
  });
}

export function adminDeleteAdmin(token: string, adminId: number) {
  return request<null>("DELETE", `/admin/admins/${adminId}`, { token });
}

export function adminListTeamAccounts(token: string) {
  return request<TeamAccountSummary[]>("GET", "/admin/team-accounts", { token });
}

// --- Feedback / Product & CX ---

export function listFeedback(token: string, filters: FeedbackFilters = {}) {
  return request<FeedbackOut[]>("GET", "/feedback", { token, query: filters });
}

export function getFeedback(token: string, feedbackId: number) {
  return request<FeedbackDetailOut>("GET", `/feedback/${feedbackId}`, { token });
}

export function feedbackMetrics(
  token: string,
  dateRange: { date_from?: string; date_to?: string } = {}
) {
  return request<FeedbackMetrics>("GET", "/feedback/metrics", { token, query: dateRange });
}

// --- Surveys ---

export function adminListSurveys(token: string) {
  return request<Survey[]>("GET", "/surveys", { token });
}

export function adminGetSurvey(token: string, surveyId: number) {
  return request<SurveyDetail>("GET", `/surveys/${surveyId}`, { token });
}

export function adminCreateSurvey(
  token: string,
  title: string,
  description: string | null,
  questions: SurveyQuestionInput[]
) {
  return request<SurveyDetail>("POST", "/surveys", { token, body: { title, description, questions } });
}

export function adminUpdateSurvey(
  token: string,
  surveyId: number,
  title: string,
  description: string | null,
  questions: SurveyQuestionInput[]
) {
  return request<SurveyDetail>("PATCH", `/surveys/${surveyId}`, {
    token,
    body: { title, description, questions },
  });
}

export function adminDeleteSurvey(token: string, surveyId: number) {
  return request<null>("DELETE", `/surveys/${surveyId}`, { token });
}

export function adminPublishSurvey(token: string, surveyId: number) {
  return request<SurveyDetail>("PATCH", `/surveys/${surveyId}/publish`, { token });
}

export function adminUnpublishSurvey(token: string, surveyId: number) {
  return request<SurveyDetail>("PATCH", `/surveys/${surveyId}/unpublish`, { token });
}

export function adminListSurveyResponses(token: string, filters: SurveyResponseFilters = {}) {
  return request<SurveyResponse[]>("GET", "/surveys/responses", { token, query: filters });
}

export function adminSurveyAnalytics(token: string, surveyId: number) {
  return request<SurveyAnalytics>("GET", `/surveys/${surveyId}/analytics`, { token });
}

export function listActiveSurveys(token: string) {
  return request<SurveyDetail[]>("GET", "/surveys/active", { token });
}

export function submitSurveyResponse(
  token: string,
  surveyId: number,
  answers: { question_id: number; value: AnswerValue }[]
) {
  return request<SurveyResponse>("POST", `/surveys/${surveyId}/responses`, {
    token,
    body: { answers },
  });
}
