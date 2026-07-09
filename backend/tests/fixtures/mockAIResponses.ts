export const validResponses = [
  {
    category: "Billing",
    priority: "Medium",
    assignedTeam: "Billing Team",
    reasoning: "Customer was charged twice for the same subscription.",
    confidence: 0.95
  },
  {
    category: "Technical Support",
    priority: "High",
    assignedTeam: "Engineering",
    reasoning: "Production API endpoint is returning 500 errors.",
    confidence: 0.97
  },
  {
    category: "Security",
    priority: "High",
    assignedTeam: "Security Team",
    reasoning: "Customer reports an unauthorized password change.",
    confidence: 0.93
  },
  {
    category: "Feature Request",
    priority: "Low",
    assignedTeam: "Engineering",
    reasoning: "Customer suggests adding a dark mode theme.",
    confidence: 0.9
  },
  {
    category: "Account Access",
    priority: "High",
    assignedTeam: "Support Team",
    reasoning: "Customer cannot log in at all and needs urgent access.",
    confidence: 0.88
  },
  {
    category: "Refund",
    priority: "Medium",
    assignedTeam: "Billing Team",
    reasoning: "Customer requests a refund for a returned damaged item.",
    confidence: 0.94
  },
  {
    category: "Shipping",
    priority: "Medium",
    assignedTeam: "Logistics",
    reasoning: "Delivery is delayed with no tracking updates.",
    confidence: 0.91
  },
  {
    category: "Sales",
    priority: "Low",
    assignedTeam: "Sales Team",
    reasoning: "Customer is asking about enterprise pricing options.",
    confidence: 0.89
  },
  {
    category: "Bug Report",
    priority: "Medium",
    assignedTeam: "QA",
    reasoning: "App crashes on launch after the latest update.",
    confidence: 0.9
  },
  {
    category: "General Inquiry",
    priority: "Low",
    assignedTeam: "Support Team",
    reasoning: "Customer is asking about support hours with no urgency.",
    confidence: 0.86
  }
];

export const malformedResponses = {
  missingField: {
    category: "Billing",
    priority: "Medium",
    assignedTeam: "Billing Team",
    confidence: 0.9
    // reasoning missing
  },
  invalidCategory: {
    category: "Foo",
    priority: "Medium",
    assignedTeam: "Billing Team",
    reasoning: "Some reason.",
    confidence: 0.9
  },
  confidenceOutOfRange: {
    category: "Billing",
    priority: "Medium",
    assignedTeam: "Billing Team",
    reasoning: "Some reason.",
    confidence: 1.5
  },
  confidenceAsString: {
    category: "Billing",
    priority: "Medium",
    assignedTeam: "Billing Team",
    reasoning: "Some reason.",
    confidence: "0.9"
  },
  codeFencedJson: '```json\n{"category":"Billing","priority":"Medium","assignedTeam":"Billing Team","reasoning":"Some reason.","confidence":0.9}\n```',
  trailingComma: '{"category":"Billing","priority":"Medium","assignedTeam":"Billing Team","reasoning":"Some reason.","confidence":0.9,}',
  proseWrapped:
    'Sure! Here\'s the JSON: {"category":"Billing","priority":"Medium","assignedTeam":"Billing Team","reasoning":"Some reason.","confidence":0.9} Hope that helps!'
};
