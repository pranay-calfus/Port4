export type Role = "USER" | "ADMIN";

export type TicketStatus =
  | "NEW"
  | "OPEN"
  | "IN_PROGRESS"
  | "PENDING_CUSTOMER"
  | "ON_HOLD"
  | "RESOLVED"
  | "CLOSED";

export const TICKET_STATUSES: TicketStatus[] = [
  "NEW",
  "OPEN",
  "IN_PROGRESS",
  "PENDING_CUSTOMER",
  "ON_HOLD",
  "RESOLVED",
  "CLOSED",
];

export type Priority = "High" | "Medium" | "Low";
export const PRIORITIES: Priority[] = ["High", "Medium", "Low"];

export type Emotion = "Neutral" | "Worried" | "Frustrated" | "Angry" | "Disappointed";

export const EMOTION_EMOJI: Record<Emotion, string> = {
  Neutral: "🫥",
  Worried: "😰",
  Frustrated: "😤",
  Angry: "😡",
  Disappointed: "😞",
};

export type Category =
  | "Billing"
  | "Technical Support"
  | "Account Access"
  | "Bug Report"
  | "Feature Request"
  | "Refund"
  | "Shipping"
  | "Sales"
  | "Security"
  | "General Inquiry"
  | "Other";

export const CATEGORIES: Category[] = [
  "Billing",
  "Technical Support",
  "Account Access",
  "Bug Report",
  "Feature Request",
  "Refund",
  "Shipping",
  "Sales",
  "Security",
  "General Inquiry",
  "Other",
];

export type AssignedTeam =
  | "Billing Team"
  | "Support Team"
  | "Engineering"
  | "QA"
  | "Security Team"
  | "Sales Team"
  | "Logistics"
  | "Customer Success";

export const ASSIGNED_TEAMS: AssignedTeam[] = [
  "Billing Team",
  "Support Team",
  "Engineering",
  "QA",
  "Security Team",
  "Sales Team",
  "Logistics",
  "Customer Success",
];

export const DEPARTMENTS: string[] = ["Unassigned", ...ASSIGNED_TEAMS];

export interface UserOut {
  id: number;
  name: string;
  email: string;
  role: Role;
  department: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export type SenderType = "USER" | "ADMIN" | "AI";

export interface MessageOut {
  id: number;
  sender_type: SenderType;
  sender_id: number | null;
  message: string;
  attachments: unknown;
  created_at: string;
}

export interface ActivityOut {
  id: number;
  event_type: string;
  detail: string | null;
  created_at: string;
}

export interface TicketOut {
  id: number;
  ticket_number: string;
  user_id: number;
  title: string;
  description: string;
  department: string;
  priority: string;
  status: TicketStatus;
  assigned_admin_id: number | null;
  ai_summary: string | null;
  ai_category: string | null;
  ai_emotion: string | null;
  ai_confidence: number | null;
  ai_priority: string | null;
  ai_processing_ms: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface TicketDetailOut extends TicketOut {
  messages: MessageOut[];
  activity: ActivityOut[];
  user: UserOut;
}

export interface AdminSummary {
  id: number;
  name: string;
  email: string;
  department: string | null;
}

export interface DepartmentMetrics {
  open_tickets: number;
  total_tickets: number;
  avg_resolution_hours: number | null;
  tickets_per_status: Record<string, number>;
  tickets_per_priority: Record<string, number>;
  tickets_per_emotion: Record<string, number>;
  tickets_per_department?: Record<string, number>;
}

export interface DashboardMetrics extends DepartmentMetrics {
  by_department?: Record<string, DepartmentMetrics>;
}

export interface AdminTicketFilters {
  department?: string;
  priority?: string;
  status_filter?: string;
  assigned_admin_id?: number;
  search?: string;
  [key: string]: string | number | undefined;
}
