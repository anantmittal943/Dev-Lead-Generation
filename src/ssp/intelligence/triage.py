import json
from openai import OpenAI
from ssp.core.config import settings
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

class TriageStage:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY
        )
        self.model = "llama-3.3-70b-versatile"

    def evaluate(self, candidate: Candidate) -> bool:
        system_prompt = """You are Stage 1 Event Triage for a premium engineering consultancy.
Your goal is to detect if a specific real-world event is occurring.

Use ONLY available evidence. Do NOT assume budget, founder status, company size, or urgency if not supported by the snippet.
If the information is incomplete, classify actor_type as UNKNOWN.

Output strictly valid JSON:
{
  "relevant": true/false,
  "event_detected": true/false,
  "actor_type": "FOUNDER" | "BUSINESS_OWNER" | "PROJECT_LEAD" | "DEVELOPER" | "STUDENT" | "UNKNOWN",
  "technical_pain": 0-100,
  "commercial_signal": 0-100,
  "urgency": 0-100,
  "confidence": 0-100,
  "reason": "..."
}"""

        user_prompt = f"""
EVENT WE ARE LOOKING FOR: {candidate.event_type}
CONTENT AVAILABILITY: {candidate.content_type}

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
                
                candidate.triage_relevant = result.get("relevant", False)
                candidate.triage_event_detected = result.get("event_detected", False)
                candidate.triage_actor_type = result.get("actor_type", "UNKNOWN")
                candidate.triage_technical_pain = result.get("technical_pain", 0)
                candidate.triage_commercial_signal = result.get("commercial_signal", 0)
                candidate.triage_urgency = result.get("urgency", 0)
                candidate.triage_confidence = result.get("confidence", 0)
                candidate.triage_reason = result.get("reason", "")
                
                return candidate.triage_relevant and candidate.triage_event_detected
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait for TPM bucket to refill
                        continue
                
                candidate.triage_relevant = False
                candidate.triage_reason = f"API Error: {str(e)}"
                return False
        return False
