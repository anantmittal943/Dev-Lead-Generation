import httpx
import urllib.parse
from typing import List, Dict
from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

class HackerNewsSource(BaseSource):
    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        from datetime import datetime, timezone
        import time
        candidates = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        cutoff_timestamp = time.time() - (max_age_days * 24 * 60 * 60)
        
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            for q_obj in queries:
                query = q_obj["query"]
                event_type = q_obj["event_type"]
                
                if verbose:
                    console.print(f"\n[cyan]SOURCE: HACKER NEWS[/cyan]")
                    console.print(f"[cyan]EVENT: {event_type}[/cyan]")
                    console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                    
                try:
                    url = f"https://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}"
                    resp = await client.get(url, follow_redirects=True)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        hits = data.get('hits', [])
                        valid_hits = 0
                        for hit in hits:
                            item_time = hit.get('created_at_i', 0)
                            if item_time < cutoff_timestamp:
                                continue
                                
                            published_at = datetime.fromtimestamp(item_time, tz=timezone.utc) if item_time else None
                            
                            candidates.append(Candidate(
                                source="Hacker News",
                                source_url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
                                title=hit.get('title') or hit.get('story_title') or '',
                                content=hit.get('story_text') or hit.get('comment_text') or '',
                                content_type="FULL_CONTENT",
                                author=hit.get('author', 'unknown'),
                                published_at=published_at,
                                query=query,
                                event_type=event_type,
                                raw_metadata=hit
                            ))
                            valid_hits += 1
                            
                        if verbose:
                            console.print(f"[green]RAW RESULTS:\n{len(hits)}[/green]")
                            console.print(f"[green]NORMALIZED:\n{valid_hits}[/green]")
                            console.print(f"────────────────────────────")
                    else:
                        if verbose:
                            console.print(f"[red]STATUS:\nFAILED[/red]")
                            console.print(f"[red]ERROR:\nHTTP {resp.status_code}[/red]")
                            console.print(f"────────────────────────────")
                except Exception as e:
                    if verbose:
                        console.print(f"[red]STATUS:\nFAILED[/red]")
                        console.print(f"[red]ERROR:\n{e}[/red]")
                        console.print(f"────────────────────────────")
                    else:
                        console.print(f"[red]HN exception during search: {e}[/red]")
                    
        return candidates
