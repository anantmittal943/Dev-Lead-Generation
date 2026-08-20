import httpx
from typing import List
from datetime import datetime, timezone
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from ssp.core.config import settings
from rich.console import Console

console = Console()

class RedditSource(BaseSource):
    def __init__(self, subreddits: str = "SaaS+startups+Entrepreneur+indiehackers+webdev"):
        self.subreddits = subreddits
        self.base_url = f"https://www.reddit.com/r/{self.subreddits}/search.json"
        
    async def search(self, queries: List[str]) -> List[Lead]:
        leads = []
        headers = {"User-Agent": settings.REDDIT_USER_AGENT}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in queries:
                try:
                    # Using search.json to allow actual query searching on Reddit
                    resp = await client.get(
                        self.base_url,
                        headers=headers,
                        params={"q": query, "restrict_sr": "on", "sort": "new", "limit": 25}
                    )
                    
                    if resp.status_code != 200:
                        console.print(f"[bold red]Reddit Error (Status {resp.status_code})[/bold red]")
                        continue
                        
                    data = resp.json()
                    for post in data.get('data', {}).get('children', []):
                        p = post['data']
                        
                        leads.append(Lead(
                            niche="", # Will be set by the orchestrator
                            source="Reddit",
                            source_id=f"reddit_{p.get('id')}",
                            title=p.get('title', ''),
                            body=p.get('selftext', ''),
                            author=p.get('author', ''),
                            source_url=f"https://www.reddit.com{p.get('permalink')}",
                            community=p.get('subreddit', ''),
                            content_type="full_content"
                        ))
                except Exception as e:
                    console.print(f"[red]Reddit exception during search: {e}[/red]")
                    
        return leads
