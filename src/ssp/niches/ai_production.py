import re
from typing import Dict, Tuple
from ssp.niches.base import BaseNiche

class AIProductionNiche(BaseNiche):
    name = "ai-production"
    description = "AI-Generated App -> Production"
    
    reddit_queries = [
        "built with cursor", "built with lovable", "vibe coded", "ai generated app"
    ]
    reddit_fallback_queries = [
        'site:reddit.com "built with Cursor" production problem',
        'site:reddit.com "built with Lovable" startup issue',
        'site:reddit.com "vibe coded" app broken',
        'site:reddit.com startup AI generated code production',
        'site:reddit.com SaaS Cursor deployment issue'
    ]
    hn_queries = [
        "built with cursor", "built with lovable", "vibe coded", "ai generated"
    ]
    web_queries = [
        'site:linkedin.com/posts "built with cursor" production',
        'site:linkedin.com/posts "built with lovable" deployment',
        'site:news.ycombinator.com "vibe coded"'
    ]

    @classmethod
    def score_candidate(cls, title: str, body: str) -> Tuple[int, Dict[str, int]]:
        text = f"{title}\n{body}".lower()
        score = 0
        breakdown = {}

        if re.search(r'\b(saas|startup|customers|paying|revenue|launch|company|business)\b', text):
            score += 25
            breakdown["Commercial context"] = 25

        if re.search(r'\b(my app|our app|founder|we built|i built)\b', text):
            score += 20
            breakdown["Founder signal"] = 20

        if re.search(r'\b(cursor|lovable|bolt|v0|replit|claude code|vibe code|ai generated)\b', text):
            score += 15
            breakdown["AI-built product"] = 15

        if re.search(r'\b(deployment|production|security|database|scaling|crashes|reliability|technical debt)\b', text):
            score += 15
            breakdown["Production pain"] = 15

        if re.search(r'\b(urgent|help|hire|looking for engineer|freelancer|stuck)\b', text):
            score += 10
            breakdown["Active intent to hire"] = 10

        if re.search(r'\b(student|homework|tutorial|toy project|no budget|equity only|learning)\b', text):
            score -= 50
            breakdown["Negative signal (hobby/student)"] = -50

        return score, breakdown

    @classmethod
    def get_system_prompt(cls, content_availability: str = "full_content") -> str:
        return f"""You are a ruthless B2B lead qualifier for a premium software engineering consultancy.
Positioning: "You built it with AI. We make it production-ready."

CONTENT AVAILABILITY: {content_availability}
Use only the available evidence. Do not assume budget, founder status, customer count, or urgency if not explicitly supported by the snippet.

PASS CRITERIA (Must meet BOTH):
1. The user built an app using an AI tool (Cursor, Lovable, Bolt, etc.).
2. They have a COMMERCIAL context (customers, startup, users) and are facing production, scaling, deployment, or technical debt issues.

FAIL CRITERIA: Hobbyists, students, learning projects, $0 budget, equity-only, or general AI coding discussions without pain.

REVIEW CRITERIA: The candidate appears potentially relevant but available information is insufficient to confidently verify commercial seriousness.

Output strictly valid JSON with no markdown blocks:
{{
  "status": "PASS" | "REVIEW" | "FAIL",
  "confidence": 0-100,
  "lead_type": "ai_production",
  "reason": "Concise explanation.",
  "pain_point_summary": "Maximum 10 words.",
  "commercial_context": "Evidence of business.",
  "urgency": "low" | "medium" | "high",
  "decision_maker_likelihood": "low" | "medium" | "high",
  "recommended_action": "ignore" | "review" | "contact"
}}"""
