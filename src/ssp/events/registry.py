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

# ---------------------------------------------------------------------------
# AI → Production Niche
# Phrases are written as real distressed users write them, not as tool names.
# ---------------------------------------------------------------------------
AI_PRODUCTION_EVENTS = [
    EventType("AI_PRODUCTION_FAILURE", "Founder who built with AI can't get to production", [
        # Deployment / infra pain
        "app keeps crashing in production",
        "can't deploy my app",
        "my app breaks when real users use it",
        "vibe coded my startup now it won't scale",
        "built my saas with AI now I'm stuck",
        "my AI-built app is down",
        "lovable app is broken",
        "cursor app crashes with multiple users",
        "bolt.new app broke after launch",
        "v0 app won't deploy",
        # DB / auth pain
        "losing user data",
        "authentication keeps breaking",
        "database is corrupting",
        "stripe payments failing on my saas",
        "users can't log in to my app",
        # General scaling pain
        "app was fine with 10 users now broken",
        "how do I make my AI app production ready",
        "hired someone to fix my vibe coded app",
        "need a developer to fix my cursor project",
    ]),
    EventType("AI_GENERATED_CODE_FAILURE", "AI-generated code is unmaintainable or failing", [
        "don't understand the code cursor wrote",
        "lovable generated spaghetti code",
        "AI code is a complete mess",
        "cursor keeps breaking things when I change something",
        "can't read this code anymore",
        "infinite loop after AI edit",
        "need a real developer to fix AI mess",
        "AI rewrote my app and now nothing works",
        "tech debt from AI coding",
        "my entire codebase is AI generated and broken",
        "no one can understand my codebase",
        "developer refused to work on AI generated code",
    ]),
    EventType("AI_APP_SEEKING_HELP", "Founder seeking engineering help for their AI-built product", [
        "looking for developer to help with my AI built saas",
        "need engineer to productionize my AI app",
        "willing to pay someone to fix my cursor app",
        "freelancer to clean up AI generated code",
        "CTO for my vibe coded startup",
        "developer to take over my lovable project",
        "engineer to fix my bolt app",
    ]),
]

AI_PRODUCTION_CONFIG = NicheEventConfig(
    niche_name="ai-production",
    events=AI_PRODUCTION_EVENTS,
    commercial_contexts=[
        "startup", "SaaS", "paying customers", "revenue", "launch",
        "production", "users", "business", "500 users", "1000 users",
    ],
    technical_contexts=[
        "app", "authentication", "database", "Stripe", "deployment",
        "backend", "API", "hosting", "server", "codebase",
    ],
    urgency_signals=[
        "urgent", "need help now", "broken", "failing", "blocked",
        "asap", "losing money", "customers complaining",
    ],
    max_queries=25
)

# ---------------------------------------------------------------------------
# Codebase Takeover Niche
# Phrases describe the actual emotional situation, not a job description.
# ---------------------------------------------------------------------------
TAKEOVER_EVENTS = [
    EventType("DIRECT_TAKEOVER", "Developer/agency abandoned the project", [
        "my developer stopped responding",
        "freelancer disappeared with my money",
        "agency went dark",
        "developer ghosted me",
        "contractor vanished",
        "developer left in the middle of the project",
        "my development team quit",
        "lost my technical cofounder",
        "CTO quit and left a mess",
        "need someone to take over my project",
        "need developer to finish my app",
        "looking for engineer to continue existing project",
        "inherit my codebase",
        "take over half built app",
        "unfinished software project",
        "half built MVP no developer",
    ]),
    EventType("RESCUE_OPPORTUNITY", "Project is broken, deadline missed, or launch blocked", [
        "app was working now everything is broken",
        "can't launch because of bugs",
        "launch deadline missed due to developer issues",
        "stuck can't launch",
        "app is broken and I have no developer",
        "previous developer's code doesn't work",
        "everything stopped working",
        "agency delivered broken software",
        "paid for software that doesn't work",
        "got scammed by a developer",
        "developer didn't finish what I paid for",
    ]),
    EventType("HIRING_REPLACEMENT", "Actively hiring a replacement or maintenance developer", [
        "hiring developer for existing project",
        "need freelancer to maintain my app",
        "looking for developer to take over existing codebase",
        "maintenance developer for my SaaS",
        "fractional CTO existing startup",
        "interim developer startup",
        "developer to inherit my project",
        "need someone to fix what my last developer left",
    ]),
    EventType("TECHNICAL_FOUNDER_DEPARTURE", "Loss of technical co-founder or lead engineer", [
        "CTO left my startup",
        "technical cofounder left",
        "lead developer resigned",
        "engineering team dissolved",
        "lost my only developer",
        "non-technical founder lost technical cofounder",
        "solo founder no technical skills developer left",
    ]),
]

TAKEOVER_CONFIG = NicheEventConfig(
    niche_name="takeover",
    events=TAKEOVER_EVENTS,
    commercial_contexts=[
        "startup", "SaaS", "business", "company", "MVP", "app",
        "paying users", "revenue", "clients", "customers",
    ],
    technical_contexts=[
        "codebase", "backend", "app", "software", "project",
        "existing code", "platform", "product", "database",
    ],
    urgency_signals=[
        "urgent", "asap", "blocked", "production issue",
        "losing money", "customers angry", "deadline",
    ],
    max_queries=25
)

EVENT_REGISTRY: Dict[str, NicheEventConfig] = {
    "ai-production": AI_PRODUCTION_CONFIG,
    "takeover": TAKEOVER_CONFIG,
}

