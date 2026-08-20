import re
from typing import Dict, Tuple
from ssp.niches.base import BaseNiche

class CodebaseTakeoverNiche(BaseNiche):
    name = "takeover"
    description = "Abandoned Codebase Rescue"
    
    reddit_queries = [
        "developer left", "previous developer", "take over codebase", "agency disappeared"
    ]
    reddit_fallback_queries = [
        'site:reddit.com startup developer left codebase',
        'site:reddit.com "previous developer" left app',
        'site:reddit.com "take over" existing codebase',
        'site:reddit.com agency disappeared software',
        'site:reddit.com technical cofounder left startup'
    ]
    hn_queries = [
        "developer left", "previous developer", "take over existing codebase"
    ]
    web_queries = [
        'site:linkedin.com/posts "developer left"',
        'site:linkedin.com/posts "previous developer"',
        'site:reddit.com/r/SaaS "take over" "codebase"'
    ]

    @classmethod
    def score_candidate(cls, title: str, body: str) -> Tuple[int, Dict[str, int]]:
        text = f"{title}\n{body}".lower()
        score = 0
        breakdown = {}

        if re.search(r'\b(saas|startup|customers|paying|revenue|company|business|existing application)\b', text):
            score += 25
            breakdown["Commercial context"] = 25

        if re.search(r'\b(my app|our app|founder|we built|we paid|hired)\b', text):
            score += 20
            breakdown["Founder signal"] = 20

        if re.search(r'\b(developer left|previous developer|agency disappeared|contractor|technical cofounder left|inherited codebase)\b', text):
            score += 20
            breakdown["Previous engineering failure"] = 20

        if re.search(r'\b(take over|maintain|continue development|need developer|looking for engineer|finish application|rescue)\b', text):
            score += 15
            breakdown["Active need for takeover"] = 15

        if re.search(r'\b(urgent|asap|deadline|production issue|blocked)\b', text):
            score += 10
            breakdown["Urgency"] = 10

        if re.search(r'\b(student|homework|tutorial|toy project|coding question|hobby)\b', text):
            score -= 50
            breakdown["Negative signal (hobby/student)"] = -50

        return score, breakdown

    @classmethod
    def get_system_prompt(cls, content_availability: str = "full_content") -> str:
        return f"""You are a ruthless B2B lead qualifier for a premium software engineering consultancy.
Positioning: "Developer left? We take over the system and get it shipping again."

CONTENT AVAILABILITY: {content_availability}
Use only the available evidence. Do not assume budget, founder status, customer count, or urgency if not explicitly supported by the snippet.

PASS CRITERIA (Must meet BOTH):
1. The user is a founder or business owner with an EXISTING codebase/product.
2. Their previous developer/agency left, or they explicitly need someone to take over, rescue, or maintain the project.

FAIL CRITERIA: Developers asking for coding help, students, zero-budget equity offers, or simple debugging questions.

REVIEW CRITERIA: The candidate appears potentially relevant but available information is insufficient to confidently verify commercial seriousness.

Output strictly valid JSON with no markdown blocks:
{{
  "status": "PASS" | "REVIEW" | "FAIL",
  "confidence": 0-100,
  "lead_type": "codebase_takeover",
  "reason": "Concise explanation.",
  "pain_point_summary": "Maximum 10 words.",
  "commercial_context": "Evidence of business.",
  "urgency": "low" | "medium" | "high",
  "decision_maker_likelihood": "low" | "medium" | "high",
  "recommended_action": "ignore" | "review" | "contact"
}}"""
