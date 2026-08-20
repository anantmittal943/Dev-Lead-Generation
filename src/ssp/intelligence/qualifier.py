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
        system_prompt = """You are Stage 2 Opportunity Qualification for a premium engineering consultancy.
Evaluate the triage data and content to classify the opportunity.

Use ONLY available evidence. For snippet-only content, it's often best to classify as WATCH and recommend manual inspection.

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
  "reason": "..."
}"""

        user_prompt = f"""
EVENT: {candidate.event_type}
CONTENT TYPE: {candidate.content_type}
TRIAGE PAIN: {candidate.triage_technical_pain}
TRIAGE COMMERCIAL: {candidate.triage_commercial_signal}
TRIAGE ACTOR: {candidate.triage_actor_type}

TITLE: {candidate.title}
CONTENT:
{candidate.content}
"""
        
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
            
            # Opportunity Score Calculation
            buyer_likelihood = 90 if candidate.triage_actor_type in ("FOUNDER", "BUSINESS_OWNER") else (50 if candidate.triage_actor_type == "UNKNOWN" else 10)
            tp = candidate.triage_technical_pain or 0
            urg = candidate.triage_urgency or 0
            cs = candidate.triage_commercial_signal or 0
            
            candidate.opportunity_score = (buyer_likelihood * 0.35) + (tp * 0.30) + (urg * 0.20) + (cs * 0.15)
            
            return candidate.qualification_status in ("HOT", "WARM", "WATCH")
            
        except Exception as e:
            candidate.qualification_status = "ERROR"
            candidate.recommended_action = f"API Error: {str(e)}"
            return False
