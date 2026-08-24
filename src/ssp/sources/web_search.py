import asyncio
from typing import List, Dict
from ddgs import DDGS
from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

class WebSearchSource(BaseSource):
    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        candidates = []
        
        # DDGS timelimit options: 'd' (day), 'w' (week), 'm' (month)
        # We default to 'w' if max_age_days <= 7
        t_limit = "d" if max_age_days <= 1 else "w" if max_age_days <= 7 else "m"
        
        def fetch_ddg(q):
            with DDGS() as ddgs:
                return list(ddgs.text(q, max_results=10, timelimit=t_limit))

        for q_obj in queries:
            query = q_obj["query"]
            event_type = q_obj["event_type"]
            
            if verbose:
                console.print(f"\n[cyan]SOURCE: WEB[/cyan]")
                console.print(f"[cyan]EVENT: {event_type}[/cyan]")
                console.print(f"[cyan]QUERY:\n{query}[/cyan]")
                
            try:
                results = await asyncio.to_thread(fetch_ddg, query)
                normalized_count = 0
                
                for r in results:
                    href = r.get('href', '')
                    if href:
                        candidates.append(Candidate(
                            source="Web Search",
                            source_url=href,
                            title=r.get('title', ''),
                            content=r.get('body', ''),
                            content_type="SNIPPET_ONLY",
                            author="Web User",
                            query=query,
                            event_type=event_type,
                            raw_metadata=r
                        ))
                        normalized_count += 1
                        
                if verbose:
                    console.print(f"[green]RAW RESULTS:\n{len(results)}[/green]")
                    console.print(f"[green]NORMALIZED:\n{normalized_count}[/green]")
                    console.print(f"────────────────────────────")
                    
                await asyncio.sleep(2)
            except Exception as e:
                if verbose:
                    console.print(f"[red]STATUS:\nFAILED[/red]")
                    console.print(f"[red]ERROR:\n{e}[/red]")
                    console.print(f"────────────────────────────")
                else:
                    console.print(f"[red]Web Search query exception ({query}): {e}[/red]")
                
        return candidates
