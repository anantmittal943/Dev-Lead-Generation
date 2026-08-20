from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EventType:
    id: str
    description: str
    phrases: List[str]

@dataclass
class NicheEventConfig:
    niche_name: str
    events: List[EventType]
    commercial_contexts: List[str]
    technical_contexts: List[str]
    urgency_signals: List[str]
    max_queries: int = 15

# --- AI Production Niche ---
AI_PRODUCTION_EVENTS = [
    EventType("AI_PRODUCTION_FAILURE", "Failed taking AI app to production", [
        "app is breaking", "can't fix", "database problem", "scaling", 
        "deployment failed", "production issue", "need help", "bug"
    ]),
    EventType("AI_GENERATED_CODE_FAILURE", "AI generated code is unmaintainable or failing", [
        "vibe coded", "built with Cursor", "built with Lovable", "AI generated", 
        "AI-built", "generated the app", "built my SaaS with"
    ])
]

AI_PRODUCTION_CONFIG = NicheEventConfig(
    niche_name="ai-production",
    events=AI_PRODUCTION_EVENTS,
    commercial_contexts=["startup", "SaaS", "business", "paying users", "customers", "production"],
    technical_contexts=["app", "codebase", "authentication", "database", "Stripe", "deployment"],
    urgency_signals=["urgent", "need help", "broken", "failing", "blocked"],
    max_queries=20
)

# --- Codebase Takeover Niche ---
TAKEOVER_EVENTS = [
    EventType("DEVELOPER_ABANDONMENT", "Developer abandoned the project", [
        "developer quit", "developer disappeared", "developer ghosted", 
        "previous developer left", "technical cofounder left", "cannot contact developer", "developer stopped responding"
    ]),
    EventType("AGENCY_ABANDONMENT", "Development agency abandoned the project", [
        "agency disappeared", "agency stopped responding", "replace development agency"
    ]),
    EventType("CODEBASE_TAKEOVER", "Need someone to take over existing codebase", [
        "inherited codebase", "abandoned codebase", "need someone to take over", 
        "replace developer", "need someone to finish", "existing app needs completion", "existing codebase needs help"
    ])
]

TAKEOVER_CONFIG = NicheEventConfig(
    niche_name="takeover",
    events=TAKEOVER_EVENTS,
    commercial_contexts=["startup", "SaaS", "business", "company", "customers"],
    technical_contexts=["app", "software", "codebase", "platform", "website"],
    urgency_signals=["urgent", "asap", "blocked", "production issue"],
    max_queries=20
)

EVENT_REGISTRY: Dict[str, NicheEventConfig] = {
    "ai-production": AI_PRODUCTION_CONFIG,
    "takeover": TAKEOVER_CONFIG
}
