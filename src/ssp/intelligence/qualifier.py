import json
from openai import OpenAI
from ssp.core.config import settings
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

class QualificationStage:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY
        )
        self.model = "llama-3.3-70b-versatile"

    def evaluate(self, candidate: Candidate) -> bool:
        # Pull pre-populated contact signals from source adapters
        raw_meta = candidate.raw_metadata or {}
        contact_hints = raw_meta.get("contact_summary", "")
        author_url_hint = candidate.author_url or ""
        author_hint = candidate.author or ""

        system_prompt = """You are Stage 2 Opportunity Qualification for a premium engineering consultancy.
Evaluate the triage data and content to classify the opportunity.

Use ONLY available evidence. For snippet-only content, it's often best to classify as WATCH and recommend manual inspection.

CONTACT EXTRACTION IS MANDATORY.
You will be given pre-populated contact signals from the source. Your job is to:
1. Use the pre-populated contact_hints if present.
2. Also scan the content for any emails, @handles, LinkedIn URLs, or website URLs.
3. Always output a contact_info string — never leave it blank. If no contact info exists at all, output: "No contact surface found. Reach via [platform] DM if possible."

Definitions:
HOT: Strong evidence of relevant technical event, decision maker, meaningful pain, commercial context, and urgency.
WARM: Relevant pain and possible commercial opportunity, but some information is missing.
WATCH: Potential signal, but insufficient information.
REJECTED: Clearly irrelevant.

Output strictly valid JSON:
{
  "status": "HOT" | "WARM" | "WATCH" | "REJECTED",
  "confidence": 0-100,
  "pain_point_summary": "...",
  "recommended_action": "...",
  "reason": "...",
  "contact_info": "..."
}"""

        user_prompt = f"""EVENT: {candidate.event_type}
CONTENT TYPE: {candidate.content_type}
TRIAGE PAIN: {candidate.triage_technical_pain}
TRIAGE COMMERCIAL: {candidate.triage_commercial_signal}
TRIAGE ACTOR: {candidate.triage_actor_type}
SOURCE: {candidate.source}
AUTHOR: {author_hint}
AUTHOR URL (pre-populated): {author_url_hint}
CONTACT HINTS (pre-populated by source adapter): {contact_hints}

TITLE: {candidate.title}
CONTENT:
{candidate.content}
"""

        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                
                result = json.loads(response.choices[0].message.content)
                
                candidate.qualification_status = result.get("status", "REJECTED")
                candidate.qualification_confidence = result.get("confidence", 0)
                candidate.pain_point_summary = result.get("pain_point_summary", "")
                candidate.recommended_action = result.get("recommended_action", "")
                candidate.contact_info = result.get("contact_info", "")
                
                # Opportunity Score Calculation
                buyer_likelihood = 90 if candidate.triage_actor_type in ("FOUNDER", "BUSINESS_OWNER") else (50 if candidate.triage_actor_type == "UNKNOWN" else 10)
                tp = candidate.triage_technical_pain or 0
                urg = candidate.triage_urgency or 0
                cs = candidate.triage_commercial_signal or 0
                
                freshness_points = 0
                if candidate.published_at:
                    from datetime import datetime, timezone
                    age = datetime.now(timezone.utc) - candidate.published_at.replace(tzinfo=timezone.utc)
                    age_hours = age.total_seconds() / 3600
                    if age_hours <= 6: freshness_points = 30
                    elif age_hours <= 24: freshness_points = 25
                    elif age_hours <= 72: freshness_points = 18
                    elif age_hours <= 7 * 24: freshness_points = 10
                
                base_score = (buyer_likelihood * 0.35) + (tp * 0.30) + (urg * 0.20) + (cs * 0.15)
                candidate.opportunity_score = min(100.0, base_score + freshness_points)
                
                return candidate.qualification_status in ("HOT", "WARM", "WATCH")
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait for TPM bucket to refill
                        continue
                
                candidate.qualification_status = "ERROR"
                candidate.recommended_action = f"API Error: {str(e)}"
                return False
        return False
