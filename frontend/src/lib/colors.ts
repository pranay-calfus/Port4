import type {
  AssignedTeam,
  Emotion,
  FeedbackCategory,
  FeedbackSentiment,
  Priority,
  TicketStatus,
  WeeklyReportSource,
} from "../api/types";

// Fixed, CVD-friendly hue palette. Order mirrors the fixed category order used
// throughout the app (never sorted by value) so a status/team/emotion always
// gets the same color everywhere it appears.
export const HUES = {
  blue: "#60a5fa",
  amber: "#f5b942",
  green: "#4ade80",
  red: "#f87171",
  orange: "#fb923c",
  teal: "#34d399",
  purple: "#a78bfa",
  pink: "#f472b6",
  gray: "#9ca3af",
} as const;

export const STATUS_COLORS: Record<TicketStatus, string> = {
  NEW: HUES.purple,
  OPEN: HUES.blue,
  IN_PROGRESS: HUES.orange,
  PENDING_CUSTOMER: HUES.amber,
  ON_HOLD: HUES.gray,
  RESOLVED: HUES.green,
  CLOSED: HUES.red,
};

export const PRIORITY_COLORS: Record<Priority, string> = {
  High: HUES.red,
  Medium: HUES.blue,
  Low: HUES.green,
};

export const EMOTION_COLORS: Record<Emotion, string> = {
  Neutral: HUES.green,
  Angry: HUES.red,
  Worried: HUES.blue,
  Frustrated: HUES.amber,
  Disappointed: HUES.purple,
};

export const TEAM_COLORS: Record<AssignedTeam, string> = {
  "Billing Team": HUES.orange,
  "Support Team": HUES.blue,
  Engineering: HUES.teal,
  QA: HUES.amber,
  "Security Team": HUES.purple,
  "Sales Team": HUES.pink,
  Logistics: HUES.red,
  "Customer Success": HUES.gray,
};

export const SENTIMENT_COLORS: Record<FeedbackSentiment, string> = {
  Positive: HUES.green,
  Neutral: HUES.gray,
  Negative: HUES.red,
};

export const FEEDBACK_CATEGORY_COLORS: Record<FeedbackCategory, string> = {
  "UI/UX": HUES.teal,
  Performance: HUES.orange,
  Pricing: HUES.pink,
  "Feature Request": HUES.blue,
  "Customer Support Experience": HUES.purple,
  "General Praise": HUES.green,
  Other: HUES.gray,
};

export const STATUS_ORDER: TicketStatus[] = [
  "NEW",
  "OPEN",
  "IN_PROGRESS",
  "PENDING_CUSTOMER",
  "ON_HOLD",
  "RESOLVED",
  "CLOSED",
];

export const PRIORITY_ORDER: Priority[] = ["High", "Medium", "Low"];

export const EMOTION_ORDER: Emotion[] = ["Neutral", "Angry", "Worried", "Frustrated", "Disappointed"];

export const TEAM_ORDER: AssignedTeam[] = [
  "Billing Team",
  "Support Team",
  "Engineering",
  "QA",
  "Security Team",
  "Sales Team",
  "Logistics",
  "Customer Success",
];

export const SENTIMENT_ORDER: FeedbackSentiment[] = ["Positive", "Neutral", "Negative"];

export const WEEKLY_REPORT_SOURCE_COLORS: Record<WeeklyReportSource, string> = {
  manual: HUES.blue,
  scheduled: HUES.purple,
};

export const WEEKLY_REPORT_SOURCE_LABELS: Record<WeeklyReportSource, string> = {
  manual: "Manual",
  scheduled: "Scheduled",
};

export const FEEDBACK_CATEGORY_ORDER: FeedbackCategory[] = [
  "UI/UX",
  "Performance",
  "Pricing",
  "Feature Request",
  "Customer Support Experience",
  "General Praise",
  "Other",
];

// Themes are free-text, AI-generated labels (see TicketRouteResult.theme /
// FeedbackClassification.theme) - there's no fixed set to build a static
// Record<Theme, color> from, unlike every other enum above. Instead, hash
// the name into the same HUES palette so a given theme always renders with
// the same color across charts/badges/reloads. "Other" (the catch-all
// bucket _top_themes folds long-tail themes into) always gets HUES.gray,
// mirroring how gray is used as the "ambiguous/other" color elsewhere
// (Customer Success, FeedbackCategory "Other").
const THEME_HUES = Object.values(HUES).filter((hue) => hue !== HUES.gray);

export function themeColor(name: string): string {
  if (name === "Other") return HUES.gray;
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  const index = Math.abs(hash) % THEME_HUES.length;
  return THEME_HUES[index];
}

export function statusLabel(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}
