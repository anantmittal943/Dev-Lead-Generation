import asyncio
from typing import List
from ddgs import DDGS
from ssp.sources.base import BaseSource
from ssp.core.models import Lead
from rich.console import Console

console = Console()

class WebSearchSource(BaseSource):
    async def search(self, queries: List[str], verbose: bool = False) -> List[Lead]:
        leads = []
        
        def fetch_ddg(q):
            # Blocking DDGS call
            with DDGS() as ddgs:
                return list(ddgs.text(q, max_results=10))

        for query in queries:
            if verbose:
                console.print(f"\n[cyan]SOURCE: WEB[/cyan]")
                console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                
            try:
                results = await asyncio.to_thread(fetch_ddg, query)
                normalized_count = 0
                
                for r in results:
                    href = r.get('href', '')
                    if href:
                        leads.append(Lead(
                            niche="",
                            source="Web Search",
                            source_id=href,
                            title=r.get('title', ''),
                            body="",
                            snippet=r.get('body', ''),
                            author="Web User",
                            source_url=href,
                            content_type="snippet_only"
                        ))
                        normalized_count += 1
                        
                if verbose:
                    console.print(f"[green]RAW RESULTS:\n{len(results)}[/green]")
                    console.print(f"[green]NORMALIZED:\n{normalized_count}[/green]")
                    console.print(f"[green]CONTENT TYPE:\nSNIPPET_ONLY[/green]")
                    console.print(f"────────────────────────────")
                    
                await asyncio.sleep(2)
            except Exception as e:
                if verbose:
                    console.print(f"[red]STATUS:\nFAILED[/red]")
                    console.print(f"[red]ERROR:\n{e}[/red]")
                    console.print(f"────────────────────────────")
                else:
                    console.print(f"[red]Web Search query exception ({query}): {e}[/red]")
                
        return leads
