import asyncio
from typing import List, Type
from sqlmodel import Session, select
from ssp.core.database import engine
from ssp.core.models import Lead, HuntRun
from ssp.niches.base import BaseNiche
from ssp.niches.ai_production import AIProductionNiche
from ssp.niches.codebase_takeover import CodebaseTakeoverNiche
from ssp.sources.reddit import RedditSource
from ssp.sources.hackernews import HackerNewsSource
from ssp.sources.web_search import WebSearchSource
from ssp.intelligence.qualifier import GroqQualifier
from rich.console import Console

console = Console()

class HuntService:
    def __init__(self):
        self.qualifier = GroqQualifier()
        
    def get_niche(self, niche_name: str) -> Type[BaseNiche]:
        if niche_name == "ai-production":
            return AIProductionNiche
        elif niche_name == "takeover":
            return CodebaseTakeoverNiche
        raise ValueError(f"Unknown niche: {niche_name}")

    async def execute_hunt(self, niche_name: str, min_score: int, verbose: bool):
        niche = self.get_niche(niche_name)
        
        with Session(engine) as session:
            run = HuntRun(niche=niche_name)
            session.add(run)
            session.commit()
            
            console.print(f"\n[bold]\[1/3] Searching Reddit[/bold]")
            reddit = RedditSource()
            reddit_leads = await reddit.search(niche.reddit_queries)
            console.print(f"✓ {len(reddit_leads)} candidates")
            
            console.print(f"\n[bold]\[2/3] Searching Hacker News[/bold]")
            hn = HackerNewsSource()
            hn_leads = await hn.search(niche.hn_queries)
            console.print(f"✓ {len(hn_leads)} candidates")
            
            console.print(f"\n[bold]\[3/3] Running web discovery[/bold]")
            web = WebSearchSource()
            web_leads = await web.search(niche.web_queries)
            console.print(f"✓ {len(web_leads)} candidates")
            
            all_raw = reddit_leads + hn_leads + web_leads
            run.raw_candidates = len(all_raw)
            
            console.print(f"\n[bold]Deduplicating...[/bold]")
            unique_leads = []
            for lead in all_raw:
                # Check DB for duplicate
                existing = session.exec(select(Lead).where(Lead.source_url == lead.source_url)).first()
                if not existing:
                    unique_leads.append(lead)
                else:
                    run.duplicates_removed += 1
                    
            console.print(f"✓ {run.duplicates_removed} duplicates removed")
            
            console.print(f"\n[bold]Analyzing signals...[/bold]")
            scored_leads = []
            for lead in unique_leads:
                lead.niche = niche_name
                score, breakdown = niche.score_candidate(lead.title, lead.body or lead.snippet or "")
                lead.deterministic_score = score
                lead.score_breakdown = breakdown
                
                if score >= min_score:
                    scored_leads.append(lead)
                else:
                    run.score_filtered += 1
            
            console.print(f"✓ {len(scored_leads)} candidates passed scoring threshold ({min_score})")
            
            console.print(f"\n[bold]Qualifying with Groq...[/bold]")
            qualified_count = 0
            
            for lead in scored_leads:
                run.llm_analyzed += 1
                passed = self.qualifier.evaluate(lead, niche.get_system_prompt())
                session.add(lead)
                if passed:
                    qualified_count += 1
                    run.qualified += 1
                    if verbose:
                        console.print(f"[green]Qualified: {lead.title} ({lead.source_url})[/green]")
                elif verbose:
                    console.print(f"[dim]Rejected: {lead.llm_reason} - {lead.source_url}[/dim]")
            
            session.commit()
            
            console.print(f"✓ {qualified_count} qualified leads found")
            
            # Print the strongest leads
            strong_leads = [l for l in scored_leads if l.llm_status == "PASS"]
            for idx, lead in enumerate(strong_leads):
                console.print(f"\n────────────────────────────────────────")
                console.print(f"[bold]LEAD #{idx+1}[/bold]")
                console.print(f"Score: {lead.deterministic_score}/100")
                console.print(f"Niche: {niche.description}")
                console.print(f"Source: {lead.source}")
                console.print(f"\nTitle:\n{lead.title}")
                console.print(f"\nPain Point:\n{lead.pain_point}")
                console.print(f"\nWhy qualified:\n{lead.llm_reason}")
                console.print(f"\nAction:\n[bold green]{str(lead.recommended_action).upper()}[/bold green] - {lead.source_url}")
                
            console.print(f"\n────────────────────────────────────────\n")
