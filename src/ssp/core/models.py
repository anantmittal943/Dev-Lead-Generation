from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON

class Query(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    niche: str
    source: str
    query_text: str
    enabled: bool = Field(default=True)
    priority: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    times_run: int = Field(default=0)
    candidates_found: int = Field(default=0)
    qualified_leads: int = Field(default=0)
    user_approved_leads: int = Field(default=0)

class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    niche: str
    source: str
    source_id: str = Field(index=True)
    title: str
    body: str
    snippet: Optional[str] = Field(default=None)
    author: str
    author_url: Optional[str] = Field(default=None)
    community: Optional[str] = Field(default=None)
    source_url: str = Field(unique=True, index=True)
    published_at: Optional[datetime] = Field(default=None)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_type: str = Field(default="full_content")  # full_content, snippet_only
    
    deterministic_score: int = Field(default=0)
    score_breakdown: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    llm_status: Optional[str] = Field(default=None) # PASS, FAIL, ERROR
    llm_confidence: Optional[int] = Field(default=None)
    llm_reason: Optional[str] = Field(default=None)
    pain_point: Optional[str] = Field(default=None)
    urgency: Optional[str] = Field(default=None)
    decision_maker_likelihood: Optional[str] = Field(default=None)
    recommended_action: Optional[str] = Field(default=None)
    
    user_verdict: Optional[str] = Field(default=None) # STRONG, MAYBE, BAD, ARCHIVED
    status: str = Field(default="new")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HuntRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    niche: str
    total_queries: int = Field(default=0)
    raw_candidates: int = Field(default=0)
    duplicates_removed: int = Field(default=0)
    signal_filtered: int = Field(default=0)
    score_filtered: int = Field(default=0)
    llm_analyzed: int = Field(default=0)
    qualified: int = Field(default=0)
    errors: int = Field(default=0)
