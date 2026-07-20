import type { AssignedTeam, Emotion, Priority, TicketStatus } from "../api/types";

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

export function statusLabel(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}
