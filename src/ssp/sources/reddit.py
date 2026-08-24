import httpx
from typing import List, Dict
from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from ssp.core.config import settings
from ssp.sources.web_search import WebSearchSource
from rich.console import Console

console = Console()

class RedditSource(BaseSource):
    def __init__(self, subreddits: str = "SaaS+startups+Entrepreneur+indiehackers+webdev+forhire+freelance+smallbusiness+nocode+AIAssistants"):
        self.subreddits = subreddits
        self.base_url = f"https://www.reddit.com/r/{self.subreddits}/search.json"
        self.consecutive_failures = 0
        self.circuit_open = False
        
    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        from datetime import datetime, timezone
        import time
        import praw
        candidates = []
        
        cutoff_timestamp = time.time() - (max_age_days * 24 * 60 * 60)
        
        reddit = None
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            try:
                reddit = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT
                )
            except Exception as e:
                if verbose:
                    console.print(f"[red]Failed to initialize PRAW: {e}[/red]")
        
        for q_obj in queries:
            query = q_obj["query"]
            event_type = q_obj["event_type"]
            
            if self.circuit_open or not reddit:
                if verbose:
                    reason = "Circuit Breaker OPEN" if self.circuit_open else "Missing OAuth Credentials"
                    console.print(f"[yellow]Skipping Reddit direct search ({reason}). Falling back to Web...[/yellow]")
                web_source = WebSearchSource()
                fallback_q = [{"query": f"site:reddit.com {query}", "event_type": event_type}]
                fallback_cands = await web_source.search(fallback_q, max_age_days=max_age_days, verbose=verbose)
                candidates.extend(fallback_cands)
                continue
            
            if verbose:
                console.print(f"\n[cyan]SOURCE: REDDIT DIRECT (PRAW)[/cyan]")
                console.print(f"[cyan]EVENT: {event_type}[/cyan]")
                console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                
            try:
                # PRAW is synchronous, we run it directly here (for scale we'd run in executor)
                subreddit = reddit.subreddit(self.subreddits)
                search_results = subreddit.search(query, sort="new", limit=25)
                
                posts_found = 0
                for submission in search_results:
                    posts_found += 1
                    item_time = submission.created_utc
                    if item_time < cutoff_timestamp:
                        continue
                        
                    published_at = datetime.fromtimestamp(item_time, tz=timezone.utc) if item_time else None
                        
                    candidates.append(Candidate(
                        source="Reddit",
                        source_url=f"https://www.reddit.com{submission.permalink}",
                        title=submission.title or '',
                        content=submission.selftext or '',
                        content_type="FULL_CONTENT",
                        author=submission.author.name if submission.author else 'unknown',
                        published_at=published_at,
                        timestamp_confidence="verified_platform",
                        query=query,
                        event_type=event_type,
                        raw_metadata={"score": submission.score, "num_comments": submission.num_comments}
                    ))
                    
                self.consecutive_failures = 0
                
                if verbose:
                    console.print(f"[green]RAW RESULTS:\n{posts_found}[/green]")
                    console.print(f"────────────────────────────")
                    
            except Exception as e:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 3:
                    self.circuit_open = True
                    
                if verbose:
                    console.print(f"[red]STATUS:\nFAILED[/red]")
                    console.print(f"[red]ERROR:\n{e}[/red]")
                    console.print(f"[yellow]FALLBACK:\nSEARCH-BASED REDDIT DISCOVERY[/yellow]")
                    console.print(f"────────────────────────────")
                
                web_source = WebSearchSource()
                fallback_q = [{"query": f"site:reddit.com {query}", "event_type": event_type}]
                fallback_cands = await web_source.search(fallback_q, max_age_days=max_age_days, verbose=verbose)
                candidates.extend(fallback_cands)
                continue
                
        return candidates
