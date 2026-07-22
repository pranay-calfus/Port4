export type Role = "USER" | "ADMIN" | "PRODUCT_CX";

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

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatMessageResponse {
  reply: string;
  history: ChatTurn[];
}

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

export type FeedbackSentiment = "Positive" | "Neutral" | "Negative";

export const SENTIMENTS: FeedbackSentiment[] = ["Positive", "Neutral", "Negative"];

export type FeedbackCategory =
  | "UI/UX"
  | "Performance"
  | "Pricing"
  | "Feature Request"
  | "Customer Support Experience"
  | "General Praise"
  | "Other";

export const FEEDBACK_CATEGORIES: FeedbackCategory[] = [
  "UI/UX",
  "Performance",
  "Pricing",
  "Feature Request",
  "Customer Support Experience",
  "General Praise",
  "Other",
];

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
  theme: string | null;
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

export interface FeedbackOut {
  id: number;
  user_id: number;
  raw_text: string;
  sentiment: FeedbackSentiment | null;
  category: FeedbackCategory | null;
  team: string | null;
  theme: string | null;
  ai_summary: string | null;
  ai_reasoning: string | null;
  ai_confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackDetailOut extends FeedbackOut {
  user: UserOut;
}

export type EscalateResponse =
  | { type: "ticket"; ticket: TicketDetailOut }
  | { type: "feedback"; feedback: FeedbackOut };

export interface FeedbackFilters {
  sentiment?: string;
  category?: string;
  team?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | undefined;
}

export interface TopTheme {
  theme: string;
  count: number;
}

export interface ThemeTrendPoint {
  date: string;
  counts: Record<string, number>;
}

export interface FeedbackMetrics {
  total_feedback: number;
  feedback_per_sentiment: Record<string, number>;
  feedback_per_category: Record<string, number>;
  feedback_per_team: Record<string, number>;
  top_themes: TopTheme[];
  theme_trend: ThemeTrendPoint[];
  date_range: DateRange;
}

export interface AdminSummary {
  id: number;
  name: string;
  email: string;
  department: string | null;
}

export interface TeamAccountSummary extends AdminSummary {
  role: Role;
}

export interface DepartmentMetrics {
  open_tickets: number;
  total_tickets: number;
  avg_resolution_hours: number | null;
  tickets_per_status: Record<string, number>;
  tickets_per_priority: Record<string, number>;
  tickets_per_emotion: Record<string, number>;
  tickets_per_category: Record<string, number>;
  tickets_per_department?: Record<string, number>;
  top_themes: TopTheme[];
  theme_trend: ThemeTrendPoint[];
}

export interface DateRange {
  from: string | null;
  to: string | null;
}

export interface DashboardMetrics extends DepartmentMetrics {
  by_department?: Record<string, DepartmentMetrics>;
  date_range: DateRange;
}

export interface AdminTicketFilters {
  department?: string;
  priority?: string;
  status_filter?: string;
  assigned_admin_id?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | number | undefined;
}

// --- Surveys ---

export type QuestionType =
  | "short_text"
  | "long_text"
  | "rating"
  | "multiple_choice"
  | "single_choice";

export const QUESTION_TYPES: QuestionType[] = [
  "short_text",
  "long_text",
  "rating",
  "multiple_choice",
  "single_choice",
];

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  short_text: "Short text",
  long_text: "Long text",
  rating: "Rating (1-5)",
  multiple_choice: "Multiple choice",
  single_choice: "Single choice",
};

export const CHOICE_QUESTION_TYPES: QuestionType[] = ["multiple_choice", "single_choice"];

export type AnswerValue = string | number | string[];

export interface SurveyQuestion {
  id: number;
  question_text: string;
  question_type: QuestionType;
  options: string[] | null;
  required: boolean;
}

export interface SurveyQuestionInput {
  question_text: string;
  question_type: QuestionType;
  options: string[] | null;
  required: boolean;
}

export interface Survey {
  id: number;
  title: string;
  description: string | null;
  is_published: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  response_count: number;
}

export interface SurveyDetail extends Survey {
  questions: SurveyQuestion[];
}

export interface SurveyAnswer {
  id: number;
  question_id: number;
  value: AnswerValue;
}

export interface SurveyResponse {
  id: number;
  survey_id: number;
  user_id: number;
  submitted_at: string;
  answers: SurveyAnswer[];
  user: UserOut;
}

export interface SurveyResponseFilters {
  survey_id?: number;
  date_from?: string;
  date_to?: string;
  rating?: number;
  question_id?: number;
  user_id?: number;
  [key: string]: string | number | undefined;
}

export interface SurveyQuestionAnalytics {
  question_id: number;
  question_text: string;
  question_type: QuestionType;
  response_count: number;
  average_rating: number | null;
  rating_distribution: Record<string, number>;
  most_common_answers: { answer: string; count: number }[];
}

export interface SurveyAnalytics {
  survey_id: number;
  total_responses: number;
  questions: SurveyQuestionAnalytics[];
}
