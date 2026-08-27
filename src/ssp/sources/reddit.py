"""
Reddit source — PAUSED.

Reddit killed self-service OAuth app registration in Nov 2025 and the
public .json URL trick returned 403 as of May 2026.  This class is kept
so nothing breaks on import, but it returns zero candidates and prints a
one-time notice so the pipeline doesn't silently skip it.
"""
from typing import List, Dict
from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

class RedditSource(BaseSource):
    """Paused — Reddit closed public API access in 2025/2026."""

    _warned = False

    def __init__(self, subreddits: str = ""):
        pass

    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        if not RedditSource._warned:
            console.print("[yellow]Reddit source is PAUSED (API access closed Nov 2025). Skipping.[/yellow]")
            RedditSource._warned = True
        return []

