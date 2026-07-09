import { TicketRouteResult } from "../types/ticket";

export interface FewShotExample {
  ticket: string;
  output: TicketRouteResult;
}

// These examples anchor the model's behavior across the exact scenarios the
// mission calls out. Each pairs a realistic ticket with the desired
// structured output, including the "why" behind priority and team choices.
export const FEW_SHOT_EXAMPLES: FewShotExample[] = [
  {
    ticket: "I forgot my password and the reset link in my email isn't working. Can you help me get back into my account?",
    output: {
      category: "Account Access",
      priority: "Medium",
      assignedTeam: "Support Team",
      reasoning: "User cannot reset their password via the normal flow, which is an account access issue but not a security incident.",
      confidence: 0.93
    }
  },
  {
    ticket: "I'd like a refund for order #55210, it arrived damaged and I already sent it back.",
    output: {
      category: "Refund",
      priority: "Medium",
      assignedTeam: "Billing Team",
      reasoning: "Customer explicitly requests a refund for a returned, damaged item.",
      confidence: 0.95
    }
  },
  {
    ticket: "Our production server has been down for 15 minutes and none of our customers can access the platform. This is critical.",
    output: {
      category: "Technical Support",
      priority: "High",
      assignedTeam: "Engineering",
      reasoning: "An active production outage affecting all customers is a critical, high-urgency infrastructure issue.",
      confidence: 0.98
    }
  },
  {
    ticket: "The app crashes every single time I open it since the last update. It's unusable right now.",
    output: {
      category: "Bug Report",
      priority: "Medium",
      assignedTeam: "QA",
      reasoning: "A reproducible crash after an update is a functional bug affecting usability, but not an active outage or security event.",
      confidence: 0.9
    }
  },
  {
    ticket: "I was charged $49.99 twice for the same subscription this month, please refund the extra charge.",
    output: {
      category: "Billing",
      priority: "Medium",
      assignedTeam: "Billing Team",
      reasoning: "Duplicate charge is a billing error requiring a refund, but it is not a production-wide payment failure.",
      confidence: 0.96
    }
  },
  {
    ticket: "I keep getting 'invalid credentials' when I try to log in, even though I know my password is correct and I need to work right now.",
    output: {
      category: "Account Access",
      priority: "High",
      assignedTeam: "Support Team",
      reasoning: "Complete inability to log in blocks the user from working, which the priority rules classify as high urgency.",
      confidence: 0.92
    }
  },
  {
    ticket: "Would it be possible to add a dark mode option to the dashboard? It would really help at night.",
    output: {
      category: "Feature Request",
      priority: "Low",
      assignedTeam: "Engineering",
      reasoning: "This is a non-urgent enhancement suggestion with no functional impact on the current product.",
      confidence: 0.94
    }
  },
  {
    ticket: "My package was supposed to arrive 4 days ago and the tracking hasn't moved. When will it actually get here?",
    output: {
      category: "Shipping",
      priority: "Medium",
      assignedTeam: "Logistics",
      reasoning: "A stalled delivery is a shipping delay affecting the customer but not a critical safety or financial issue.",
      confidence: 0.91
    }
  },
  {
    ticket: "The /v1/orders endpoint in your API has been returning 500 errors for the last hour and it's breaking our integration.",
    output: {
      category: "Technical Support",
      priority: "High",
      assignedTeam: "Engineering",
      reasoning: "A broken production API endpoint actively disrupting a customer integration is a high-urgency technical issue.",
      confidence: 0.95
    }
  },
  {
    ticket: "I just received an email saying my password was changed, but I never did that. I think my account has been compromised.",
    output: {
      category: "Security",
      priority: "High",
      assignedTeam: "Security Team",
      reasoning: "An unauthorized account change strongly suggests a security breach, which is always treated as high priority.",
      confidence: 0.93
    }
  },
  {
    ticket: "Please cancel my subscription immediately, I don't want to be billed again next cycle.",
    output: {
      category: "Billing",
      priority: "Medium",
      assignedTeam: "Billing Team",
      reasoning: "A subscription cancellation request is a standard billing action with no urgent safety or outage component.",
      confidence: 0.95
    }
  },
  {
    ticket: "The invoice I received (INV-3391) shows a charge that's $25 more than the plan I actually signed up for.",
    output: {
      category: "Billing",
      priority: "Medium",
      assignedTeam: "Billing Team",
      reasoning: "A discrepancy between the invoiced amount and the agreed plan is a billing accuracy issue requiring correction.",
      confidence: 0.92
    }
  }
];
