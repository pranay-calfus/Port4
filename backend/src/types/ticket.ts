export const CATEGORIES = [
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
  "Other"
] as const;

export const PRIORITIES = ["High", "Medium", "Low"] as const;

export const ASSIGNED_TEAMS = [
  "Billing Team",
  "Support Team",
  "Engineering",
  "QA",
  "Security Team",
  "Sales Team",
  "Logistics",
  "Customer Success"
] as const;

export type Category = (typeof CATEGORIES)[number];
export type Priority = (typeof PRIORITIES)[number];
export type AssignedTeam = (typeof ASSIGNED_TEAMS)[number];

export interface TicketRouteResult {
  category: Category;
  priority: Priority;
  assignedTeam: AssignedTeam;
  reasoning: string;
  confidence: number;
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  processingTime: string;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    message: string;
    code: string;
    details?: unknown;
  };
}
