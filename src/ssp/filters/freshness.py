from datetime import datetime, timezone, timedelta

MAX_AGE_DAYS = 7

class FreshnessFilter:
    def __init__(self, max_age_days: int = MAX_AGE_DAYS):
        self.max_age_days = max_age_days

    def evaluate(self, candidate):
        published_at = getattr(candidate, "published_at", None)

        # If no timestamp could be resolved (e.g. web snippets from DuckDuckGo),
        # allow the candidate through but flag it as low-confidence instead of
        # hard-rejecting it.  The LLM triage stage is better equipped to judge
        # relevance than a date-gating rule that has no date to work with.
        if published_at is None:
            return {
                "accepted": True,
                "reason": "TIMESTAMP_UNVERIFIED",
                "age_days": None
            }

        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age = now - published_at

        if age > timedelta(days=self.max_age_days):
            return {
                "accepted": False,
                "reason": "STALE",
                "age_days": age.days
            }

        return {
            "accepted": True,
            "reason": "FRESH",
            "age_days": age.days
        }
