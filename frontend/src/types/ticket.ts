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

export type Priority = "High" | "Medium" | "Low";

export type AssignedTeam =
  | "Billing Team"
  | "Support Team"
  | "Engineering"
  | "QA"
  | "Security Team"
  | "Sales Team"
  | "Logistics"
  | "Customer Success";

export interface TicketRouteResult {
  category: Category;
  priority: Priority;
  assignedTeam: AssignedTeam;
  reasoning: string;
  confidence: number;
}

export interface ApiSuccessResponse {
  success: true;
  data: TicketRouteResult;
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

export interface SampleTicket {
  id: string;
  title: string;
  categoryLabel: string;
  message: string;
  expectedCategory?: Category;
  expectedPriority?: Priority;
}
