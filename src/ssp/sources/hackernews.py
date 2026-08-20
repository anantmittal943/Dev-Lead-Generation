import httpx
import urllib.parse
from typing import List
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from rich.console import Console

console = Console()

class HackerNewsSource(BaseSource):
    async def search(self, queries: List[str]) -> List[Lead]:
        leads = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in queries:
                try:
                    url = f"http://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}&tags=story"
                    resp = await client.get(url)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        for hit in data.get('hits', []):
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
                except Exception as e:
                    console.print(f"[red]HN exception during search: {e}[/red]")
                    
        return leads
