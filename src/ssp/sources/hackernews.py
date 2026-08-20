import httpx
import urllib.parse
from typing import List
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from rich.console import Console

console = Console()

class HackerNewsSource(BaseSource):
    async def search(self, queries: List[str], fallback_queries: List[str] = None, verbose: bool = False) -> List[Lead]:
        leads = []
        # Add realistic User-Agent to prevent Algolia 403 blocks
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            for query in queries:
                if verbose:
                    console.print(f"\n[cyan]SOURCE: HACKER NEWS[/cyan]")
                    console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                    
                try:
                    url = f"http://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}&tags=story"
                    resp = await client.get(url)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        hits = data.get('hits', [])
                        valid_hits = 0
                        for hit in hits:
                            leads.append(Lead(
                                niche="",
                                source="Hacker News",
                                source_id=f"hn_{hit['objectID']}",
                                title=hit.get('title', ''),
                                body=hit.get('story_text', '') or '',
                                author=hit.get('author', 'unknown'),
                                source_url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
                                content_type="full_content"
                            ))
                            valid_hits += 1
                            
                        if verbose:
                            console.print(f"[green]RAW RESULTS:\n{len(hits)}[/green]")
                            console.print(f"[green]NORMALIZED:\n{valid_hits}[/green]")
                            console.print(f"[green]CONTENT TYPE:\nFULL_CONTENT[/green]")
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
                    
        return leads
