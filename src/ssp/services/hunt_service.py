import asyncio
import re
from typing import List, Type
from sqlmodel import Session, select
from ssp.core.database import engine
from ssp.core.models import Candidate, HuntRun, QueryPerformance
from ssp.events.registry import EVENT_REGISTRY, NicheEventConfig
from ssp.events.query_generator import EventQueryGenerator
from ssp.sources.reddit import RedditSource
from ssp.sources.hackernews import HackerNewsSource
from ssp.sources.web_search import WebSearchSource
from ssp.sources.devto import DevToSource
from ssp.sources.indiehackers import IndieHackersSource
from ssp.intelligence.triage import TriageStage
from ssp.intelligence.qualifier import QualificationStage
from rich.console import Console
from rich.panel import Panel

console = Console()

class HuntService:
    def __init__(self):
        self.triage = TriageStage()
        self.qualifier = QualificationStage()
        
    def _basic_garbage_filter(self, text: str) -> bool:
        """Returns True if the text is obvious garbage and should be rejected."""
        t = text.lower()
        if re.search(r'\b(tutorial|how to|documentation|github\.com/.*/blob|stackoverflow|course|learning|homework)\b', t):
            return True
        return False

    async def execute_hunt(self, niche_name: str, verbose: bool, limit: int = None, source: str = None, max_age_days: int = 7, dry_run: bool = False):
        if niche_name not in EVENT_REGISTRY:
            console.print(f"[bold red]Unknown niche: {niche_name}[/bold red]")
            return
            
        config: NicheEventConfig = EVENT_REGISTRY[niche_name]
        queries = EventQueryGenerator.generate_queries(config)
        
        if limit:
            queries = queries[:limit]
            
        console.print(f"Generating event queries...\n✓ {len(queries)} queries")
        
        console.print(f"\n[bold]Discovering opportunities...[/bold]\n")
        
        all_raw_candidates: List[Candidate] = []
        
        with Session(engine) as session:
            run = HuntRun(niche=niche_name, queries_generated=len(queries))
            if not dry_run:
                session.add(run)
                session.commit()
            
            # --- Discovery ---
            # Reddit is paused (API closed 2025/2026) — kept as stub, returns [].
            if not source or source.lower() == "reddit":
                reddit = RedditSource()
                reddit_leads = await reddit.search(queries, max_age_days=max_age_days, verbose=verbose)
                if reddit_leads:
                    console.print(f"Reddit Discovery\n✓ {len(reddit_leads)} candidates\n")
                    all_raw_candidates.extend(reddit_leads)

            if not source or source.lower() == "hn":
                hn = HackerNewsSource()
                hn_leads = await hn.search(queries, max_age_days=max_age_days, verbose=verbose)
                console.print(f"Hacker News\n✓ {len(hn_leads)} candidates\n")
                all_raw_candidates.extend(hn_leads)

            if not source or source.lower() == "devto":
                devto = DevToSource()
                devto_leads = await devto.search(queries, max_age_days=max_age_days, verbose=verbose)
                console.print(f"dev.to\n✓ {len(devto_leads)} candidates\n")
                all_raw_candidates.extend(devto_leads)

            if not source or source.lower() == "ih":
                ih = IndieHackersSource()
                ih_leads = await ih.search(queries, max_age_days=max_age_days, verbose=verbose)
                console.print(f"Indie Hackers\n✓ {len(ih_leads)} candidates\n")
                all_raw_candidates.extend(ih_leads)

            if not source or source.lower() == "web":
                web = WebSearchSource()
                web_leads = await web.search(queries, max_age_days=max_age_days, verbose=verbose)
                console.print(f"Web Search\n✓ {len(web_leads)} candidates\n")
                all_raw_candidates.extend(web_leads)

                
            run.raw_candidates = len(all_raw_candidates)
            
            console.print(f"────────────────────────────────\n")
            console.print(f"Raw candidates\n{run.raw_candidates}\n")

            # --- Deduplication ---
            unique_candidates = []
            seen_urls = set()
            for cand in all_raw_candidates:
                if cand.source_url in seen_urls:
                    run.duplicates_removed += 1
                    continue
                    
                if not dry_run:
                    existing = session.exec(select(Candidate).where(Candidate.source_url == cand.source_url)).first()
                    if existing:
                        run.duplicates_removed += 1
                        continue
                        
                seen_urls.add(cand.source_url)
                unique_candidates.append(cand)
                
            console.print(f"Duplicates removed\n{run.duplicates_removed}\n")

            # --- Timestamp Resolution ---
            from ssp.processing.timestamp_resolver import TimestampResolver
            console.print(f"Resolving timestamps for {len(unique_candidates)} candidates...")
            
            async def resolve_batch(cands):
                tasks = [TimestampResolver.resolve(c, verbose=verbose) for c in cands]
                return await asyncio.gather(*tasks)
                
            resolved_candidates = await resolve_batch(unique_candidates)

            # --- Freshness Filter ---
            from ssp.filters.freshness import FreshnessFilter
            freshness_filter = FreshnessFilter(max_age_days=max_age_days)
            fresh_candidates = []
            
            for cand in resolved_candidates:
                f_result = freshness_filter.evaluate(cand)
                if not f_result["accepted"]:
                    if verbose:
                        console.print(f"[dim]STALE REJECTED ({f_result.get('age_days', 'unknown')} days): {cand.title}[/dim]")
                    continue
                fresh_candidates.append(cand)
                
            console.print(f"Fresh candidates (<= {max_age_days} days)\n{len(fresh_candidates)}\n")
            
            # --- Garbage Filter ---
            filtered_candidates = []
            for cand in fresh_candidates:
                full_text = f"{cand.title} {cand.content}"
                if self._basic_garbage_filter(full_text):
                    run.garbage_rejected += 1
                    cand.garbage_filtered = True
                    if verbose:
                        console.print(f"[dim]GARBAGE FILTER REJECTED: {cand.title}[/dim]")
                else:
                    filtered_candidates.append(cand)
                    
            console.print(f"Garbage rejected\n{run.garbage_rejected}\n")
            
            # --- LLM Stage 1: Triage ---
            console.print(f"Sent to Event Triage\n{len(filtered_candidates)}\n")
            
            triaged_relevant = []
            for cand in filtered_candidates:
                run.triage_analyzed += 1
                cand.niche = niche_name
                is_relevant = self.triage.evaluate(cand)
                if is_relevant:
                    triaged_relevant.append(cand)
                    run.triage_relevant += 1
                    if verbose:
                        console.print(f"[cyan]TRIAGE RELEVANT: {cand.event_type} - {cand.title}[/cyan]")
                else:
                    if verbose:
                        console.print(f"[dim]TRIAGE REJECTED: {cand.triage_reason}[/dim]")
                        
            console.print(f"Relevant events\n{run.triage_relevant}\n")
            
            # --- LLM Stage 2: Qualification ---
            hot_count = warm_count = watch_count = 0
            
            for cand in triaged_relevant:
                run.deep_qualified += 1
                self.qualifier.evaluate(cand)
                
                if cand.qualification_status == "HOT": hot_count += 1
                elif cand.qualification_status == "WARM": warm_count += 1
                elif cand.qualification_status == "WATCH": watch_count += 1
                
                if verbose:
                    console.print(f"────────────────────────")
                    console.print(f"SOURCE: {cand.source}")
                    console.print(f"EVENT: {cand.event_type}")
                    console.print(f"QUERY: {cand.query}")
                    console.print(f"ACTOR: {cand.triage_actor_type}")
                    console.print(f"STATUS: [bold]{cand.qualification_status}[/bold]")
                    if cand.opportunity_score is not None:
                        console.print(f"SCORE: {cand.opportunity_score:.1f}")
                    console.print(f"REASON: {cand.qualification_status} - {cand.pain_point_summary}")
                
            console.print(f"Deep qualified\n{run.deep_qualified}\n")
            console.print(f"────────────────────────────────\n")
            console.print(f"🔥 HOT\n{hot_count}\n")
            console.print(f"🟡 WARM\n{warm_count}\n")
            console.print(f"👀 WATCH\n{watch_count}\n")
            
            run.hot_leads = hot_count
            run.warm_leads = warm_count
            run.watch_leads = watch_count
            
            # Update Query Performance Tracker & Save Candidates
            if not dry_run:
                for cand in unique_candidates:
                    session.add(cand)
                    
                    if cand.query:
                        perf = session.exec(select(QueryPerformance).where(QueryPerformance.query == cand.query)).first()
                        if not perf:
                            perf = QueryPerformance(query=cand.query, event_type=cand.event_type, source=cand.source)
                            session.add(perf)
                        
                        perf.times_run += 1
                        perf.raw_candidates += 1
                        if getattr(cand, "triage_relevant", False):
                            perf.relevant_candidates += 1
                        if getattr(cand, "qualification_status", "") == "HOT":
                            perf.hot_leads += 1
                        elif getattr(cand, "qualification_status", "") == "WARM":
                            perf.warm_leads += 1
                        elif getattr(cand, "qualification_status", "") == "REJECTED":
                            perf.rejected_candidates += 1
                
                session.commit()
