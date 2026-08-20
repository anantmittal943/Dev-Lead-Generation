import json
from openai import OpenAI
from ssp.core.config import settings
from ssp.core.models import Lead
from rich.console import Console

console = Console()

class GroqQualifier:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY
        )
        # We'll use 3.3 if available, but fallback to 3.1 or 8192 if needed based on previous debugging
        # As per instructions: "llama-3.3-70b-versatile"
        self.model = "llama-3.3-70b-versatile"

    def evaluate(self, lead: Lead, system_prompt: str) -> bool:
        """Evaluate a lead using the LLM. Returns True if passed, False otherwise."""
        user_prompt = f"TITLE: {lead.title}\n\nCONTENT:\n{lead.body}\n{lead.snippet or ''}"
        
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
            
            lead.llm_status = result.get("status", "FAIL")
            lead.llm_confidence = result.get("confidence", 0)
            lead.llm_reason = result.get("reason", "")
            lead.pain_point = result.get("pain_point_summary", "")
            lead.urgency = result.get("urgency", "low")
            lead.decision_maker_likelihood = result.get("decision_maker_likelihood", "low")
            lead.recommended_action = result.get("recommended_action", "ignore")
            
            return lead.llm_status in ("PASS", "REVIEW")
            
        except Exception as e:
            # Handle decommissioned models or model_not_found errors
            error_str = str(e).lower()
            if "model_not_found" in error_str or "model_decommissioned" in error_str:
                if self.model != "llama3-70b-8192":
                    self.model = "llama3-70b-8192"
                    return self.evaluate(lead, system_prompt)
                
            lead.llm_status = "ERROR"
            lead.llm_reason = f"API Error: {str(e)}"
            console.print(f"[dim red]LLM API Error on lead {lead.source_id}: {e}[/dim red]")
            return False
