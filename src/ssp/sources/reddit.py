import httpx
from typing import List, Dict
from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from ssp.core.config import settings
from ssp.sources.web_search import WebSearchSource
from rich.console import Console

console = Console()

class RedditSource(BaseSource):
    def __init__(self, subreddits: str = "SaaS+startups+Entrepreneur+indiehackers+webdev"):
        self.subreddits = subreddits
        self.base_url = f"https://www.reddit.com/r/{self.subreddits}/search.json"
        
    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        from datetime import datetime, timezone
        import time
        candidates = []
        headers = {"User-Agent": settings.REDDIT_USER_AGENT}
        
        cutoff_timestamp = time.time() - (max_age_days * 24 * 60 * 60)
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for q_obj in queries:
                query = q_obj["query"]
                event_type = q_obj["event_type"]
                
                if verbose:
                    console.print(f"\n[cyan]SOURCE: REDDIT DIRECT[/cyan]")
                    console.print(f"[cyan]EVENT: {event_type}[/cyan]")
                    console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                    
                try:
                    resp = await client.get(
                        self.base_url,
                        headers=headers,
                        params={"q": query, "restrict_sr": "on", "sort": "new", "limit": 25}
                    )
                    
                    if resp.status_code != 200:
                        if verbose:
                            console.print(f"[red]STATUS:\nFAILED[/red]")
                            console.print(f"[red]ERROR:\nHTTP {resp.status_code}[/red]")
                        
                        # Trigger Fallback explicitly for this query
                        if verbose:
                            console.print(f"[yellow]FALLBACK:\nSEARCH-BASED REDDIT DISCOVERY[/yellow]")
                            console.print(f"────────────────────────────")
                        
                        web_source = WebSearchSource()
                        fallback_q = [{"query": f"site:reddit.com {query}", "event_type": event_type}]
                        fallback_cands = await web_source.search(fallback_q, max_age_days=max_age_days, verbose=verbose)
                        candidates.extend(fallback_cands)
                        continue
                        
                    data = resp.json()
                    children = data.get('data', {}).get('children', [])
                    for post in children:
                        p = post['data']
                        item_time = p.get('created_utc', 0)
                        if item_time < cutoff_timestamp:
                            continue
                            
                        published_at = datetime.fromtimestamp(item_time, tz=timezone.utc) if item_time else None
                            
                        candidates.append(Candidate(
                            source="Reddit",
                            source_url=f"https://www.reddit.com{p.get('permalink')}",
                            title=p.get('title', ''),
                            content=p.get('selftext', ''),
                            content_type="FULL_CONTENT",
                            author=p.get('author', ''),
                            published_at=published_at,
                            query=query,
                            event_type=event_type,
                            raw_metadata=p
                        ))
                    if verbose:
                        console.print(f"[green]RAW RESULTS:\n{len(children)}[/green]")
                        console.print(f"[green]NORMALIZED:\n{len(children)}[/green]")
                        console.print(f"────────────────────────────")
                        
                except Exception as e:
                    if verbose:
                        console.print(f"[red]STATUS:\nFAILED[/red]")
                        console.print(f"[red]ERROR:\n{e}[/red]")
                        console.print(f"────────────────────────────")
                    else:
                        console.print(f"[red]Reddit exception during search: {e}[/red]")
                    
        return candidates
