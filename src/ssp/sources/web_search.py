import asyncio
from typing import List
from duckduckgo_search import DDGS
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from rich.console import Console

console = Console()

class WebSearchSource(BaseSource):
    async def search(self, queries: List[str]) -> List[Lead]:
        leads = []
        
        # DuckDuckGo is synchronous and can be blocking, so we'll wrap it gently
        def fetch_ddg(q):
            with DDGS() as ddgs:
                return list(ddgs.text(q, max_results=10))

        for query in queries:
            try:
                # Run the blocking fetch in a thread
                results = await asyncio.to_thread(fetch_ddg, query)
                for r in results:
                    href = r.get('href', '')
                    if href:
                        leads.append(Lead(
                            niche="",
                            source="Web Search",
                            source_id=href,  # URL as ID for web search
                            title=r.get('title', ''),
                            body="",
                            snippet=r.get('body', ''),
                            author="Web User",
                            source_url=href,
                            content_type="snippet_only"
                        ))
                await asyncio.sleep(2) # Be polite to DDG
            except Exception as e:
                console.print(f"[red]Web Search exception: {e}[/red]")
                
        return leads
