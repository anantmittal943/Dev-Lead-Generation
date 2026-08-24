from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON

class QueryPerformance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    event_type: str = Field(index=True)
    source: str
    times_run: int = Field(default=0)
    raw_candidates: int = Field(default=0)
    relevant_candidates: int = Field(default=0)
    hot_leads: int = Field(default=0)
    warm_leads: int = Field(default=0)
    rejected_candidates: int = Field(default=0)
    last_run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    niche: str = Field(default="unknown")
    source: str
    source_url: str = Field(unique=True, index=True)
    title: str
    content: str
    content_type: str = Field(default="FULL_CONTENT")
    author: Optional[str] = Field(default=None)
    author_url: Optional[str] = Field(default=None)
    published_at: Optional[datetime] = Field(default=None)
    timestamp_confidence: Optional[str] = Field(default=None)
    query: str = Field(default="")
    event_type: str = Field(default="")
    raw_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Garbage filter
    garbage_filtered: bool = Field(default=False)
    
    # Stage 1: Triage
    triage_relevant: Optional[bool] = Field(default=None)
    triage_event_detected: Optional[bool] = Field(default=None)
    triage_actor_type: Optional[str] = Field(default=None)
    triage_technical_pain: Optional[int] = Field(default=None)
    triage_commercial_signal: Optional[int] = Field(default=None)
    triage_urgency: Optional[int] = Field(default=None)
    triage_confidence: Optional[int] = Field(default=None)
    triage_reason: Optional[str] = Field(default=None)
    
    # Stage 2: Qualification
    qualification_status: Optional[str] = Field(default=None) # HOT, WARM, WATCH, REJECTED
    qualification_confidence: Optional[int] = Field(default=None)
    pain_point_summary: Optional[str] = Field(default=None)
    recommended_action: Optional[str] = Field(default=None)
    contact_info: Optional[str] = Field(default=None)
    
    # Final scoring
    opportunity_score: Optional[float] = Field(default=None)

class HuntRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    niche: str
    queries_generated: int = Field(default=0)
    raw_candidates: int = Field(default=0)
    duplicates_removed: int = Field(default=0)
    garbage_rejected: int = Field(default=0)
    triage_analyzed: int = Field(default=0)
    triage_relevant: int = Field(default=0)
    deep_qualified: int = Field(default=0)
    hot_leads: int = Field(default=0)
    warm_leads: int = Field(default=0)
    watch_leads: int = Field(default=0)
    errors: int = Field(default=0)
