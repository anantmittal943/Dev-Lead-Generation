import httpx
from typing import List
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from ssp.core.config import settings
from ssp.sources.web_search import WebSearchSource
from rich.console import Console

console = Console()

class RedditSource(BaseSource):
    def __init__(self, subreddits: str = "SaaS+startups+Entrepreneur+indiehackers+webdev"):
        self.subreddits = subreddits
        self.base_url = f"https://www.reddit.com/r/{self.subreddits}/search.json"
        
    async def search(self, queries: List[str], fallback_queries: List[str] = None, verbose: bool = False) -> List[Lead]:
        leads = []
        headers = {"User-Agent": settings.REDDIT_USER_AGENT}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in queries:
                if verbose:
                    console.print(f"\n[cyan]SOURCE: REDDIT DIRECT[/cyan]")
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
                        
                        # Trigger Fallback if we hit a 403 or similar and we haven't already
                        if fallback_queries:
                            if verbose:
                                console.print(f"[yellow]FALLBACK:\nSEARCH-BASED REDDIT DISCOVERY[/yellow]")
                                console.print(f"────────────────────────────")
                            web_source = WebSearchSource()
                            return await web_source.search(fallback_queries, verbose=verbose)
                        else:
                            console.print(f"[red]Reddit Error (Status {resp.status_code}) with no fallback[/red]")
                            console.print(f"────────────────────────────")
                        continue
                        
                    data = resp.json()
                    children = data.get('data', {}).get('children', [])
                    for post in children:
                        p = post['data']
                        leads.append(Lead(
                            niche="",
                            source="Reddit",
                            source_id=f"reddit_{p.get('id')}",
                            title=p.get('title', ''),
                            body=p.get('selftext', ''),
                            author=p.get('author', ''),
                            source_url=f"https://www.reddit.com{p.get('permalink')}",
                            community=p.get('subreddit', ''),
                            content_type="full_content"
                        ))
                    if verbose:
                        console.print(f"[green]RAW RESULTS:\n{len(children)}[/green]")
                        console.print(f"[green]NORMALIZED:\n{len(children)}[/green]")
                        console.print(f"[green]CONTENT TYPE:\nFULL_CONTENT[/green]")
                        console.print(f"────────────────────────────")
                        
                except Exception as e:
                    if verbose:
                        console.print(f"[red]STATUS:\nFAILED[/red]")
                        console.print(f"[red]ERROR:\n{e}[/red]")
                        console.print(f"────────────────────────────")
                    else:
                        console.print(f"[red]Reddit exception during search: {e}[/red]")
                    
        return leads
