import sys
import typer
import asyncio
from rich.console import Console

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from rich.panel import Panel

app = typer.Typer(
    help="SSP HUNTER - Engineering Opportunity Intelligence",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

def init_db(reset: bool = False):
    from ssp.core.database import engine
    from sqlmodel import SQLModel
    import ssp.core.models # load models
    if reset:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

@app.command()
def hunt(
    niche: str = typer.Argument(..., help="Niche to hunt for: 'ai-production', 'takeover'"),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose output"),
    limit: int = typer.Option(None, help="Limit number of generated queries"),
    source: str = typer.Option(None, help="Filter by specific source (reddit, hn, web)"),
    max_age_days: int = typer.Option(7, "--max-age-days", help="Maximum age of leads in days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not save to database")
):
    """Discover new opportunities via Event Intelligence."""
    console.print(Panel(f"Running {niche.upper()} event hunt", title="SSP HUNTER", border_style="cyan"))
    
    if not dry_run:
        init_db()
    
    from ssp.services.hunt_service import HuntService
    service = HuntService()
    
    try:
        asyncio.run(service.execute_hunt(niche, verbose=verbose, limit=limit, source=source, max_age_days=max_age_days, dry_run=dry_run))
    finally:
        from ssp.core.database import engine
        engine.dispose()

@app.command()
def leads(
    niche: str = typer.Option(None, help="Filter by niche"),
    status: str = typer.Option(None, help="Filter by status (HOT, WARM, WATCH)"),
    export: str = typer.Option(None, "--export", "-e", help="Export to CSV file path")
):
    """Browse saved leads."""
    from ssp.core.database import engine
    from sqlmodel import Session, select
    from ssp.core.models import Candidate
    from rich.table import Table
    import csv
    
    with Session(engine) as session:
        query = select(Candidate)
        if niche: query = query.where(Candidate.niche == niche)
        if status: query = query.where(Candidate.qualification_status == status)
        
        results = session.exec(query).all()

        if export:
            with open(export, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Niche", "Title", "Status", "Score", "Event Type", "Source", "Source URL", "Contact Info", "Pain Point Summary", "Recommended Action"])
                for cand in results:
                    writer.writerow([
                        cand.id, cand.niche, cand.title, cand.qualification_status, cand.opportunity_score,
                        cand.event_type, cand.source, cand.source_url, cand.contact_info,
                        cand.pain_point_summary, cand.recommended_action
                    ])
            console.print(f"[green]Successfully exported {len(results)} leads to {export}[/green]")
            return
        
        table = Table(title="SSP Hunter Opportunities")
        table.add_column("ID", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Niche", style="magenta")
        table.add_column("Title", style="white")
        table.add_column("Status", style="blue")
        
        for cand in results:
            table.add_row(
                str(cand.id),
                f"{cand.opportunity_score:.1f}" if cand.opportunity_score else "N/A",
                cand.niche,
                cand.title[:50] + ("..." if len(cand.title)>50 else ""),
                cand.qualification_status or "UNRATED"
            )
            
        console.print(table)
        
@app.command()
def lead(lead_id: int = typer.Argument(..., help="ID of the lead to view")):
    """View details for a specific lead."""
    from ssp.core.database import engine
    from sqlmodel import Session
    from ssp.core.models import Candidate
    from rich.markdown import Markdown as RichMarkdown
    
    with Session(engine) as session:
        cand = session.get(Candidate, lead_id)
        if not cand:
            console.print(f"[red]Lead {lead_id} not found.[/red]")
            return
            
        md = f"""# {cand.title}
**ID:** {cand.id} | **Niche:** {cand.niche} | **Status:** {cand.qualification_status}
**Score:** {cand.opportunity_score} | **Event Type:** {cand.event_type}
**Source:** [{cand.source}]({cand.source_url})
**Contact Info:** {cand.contact_info or "None found"}

## Pain Point Summary
{cand.pain_point_summary or "N/A"}

## Recommended Action
{cand.recommended_action or "N/A"}

## Triage Reason
{cand.triage_reason or "N/A"}

## Content Snippet
{cand.content[:500]}...
"""
        console.print(RichMarkdown(md))
        
@app.command()
def config(reset_db: bool = typer.Option(False, "--reset-db", help="WARNING: Drop and recreate all database tables")):
    """Configure the application."""
    if reset_db:
        console.print("[bold red]WARNING: Dropping all tables and recreating schema...[/bold red]")
        init_db(reset=True)
        console.print("[green]Database reset complete.[/green]")
        
    from ssp.core.config import settings
    console.print("[bold green]Configuration Loaded[/bold green]")
    console.print(f"Groq API Key: {'[green]✓ Configured[/green]' if settings.GROQ_API_KEY else '[red]✗ Missing[/red]'}")
    console.print(f"Reddit User Agent: {'[green]✓ Configured[/green]' if settings.REDDIT_USER_AGENT else '[red]✗ Missing[/red]'}")
    console.print(f"Database URL: {settings.DATABASE_URL}")

@app.command()
def doctor():
    """Check environment health and source access."""
    import httpx
    from rich.console import Console
    from ssp.core.config import settings
    console = Console()
    
    console.print("[bold]Checking sources and environment...[/bold]\n")
    
    # Check Groq
    if settings.GROQ_API_KEY:
        console.print("✓ [green]Groq API Key configured[/green]")
    else:
        console.print("✗ [red]Groq API Key missing[/red]")
        
    # Check Reddit
    try:
        resp = httpx.get("https://www.reddit.com/r/startups/search.json?q=test", headers={"User-Agent": settings.REDDIT_USER_AGENT})
        if resp.status_code == 200:
            console.print("✓ [green]Reddit API accessible[/green]")
        else:
            console.print(f"✗ [red]Reddit API HTTP {resp.status_code}[/red]")
            console.print("  [dim]Reddit native source will be disabled or fallback to Web.[/dim]")
    except Exception as e:
        console.print(f"✗ [red]Reddit API error: {e}[/red]")
        
    # Check Hacker News
    try:
        resp = httpx.get("https://hn.algolia.com/api/v1/search?query=test")
        if resp.status_code == 200:
            console.print("✓ [green]Hacker News API accessible[/green]")
        else:
            console.print(f"✗ [red]Hacker News API HTTP {resp.status_code}[/red]")
    except Exception as e:
        console.print(f"✗ [red]Hacker News API error: {e}[/red]")
        
    # Check Web Search
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            list(ddgs.text("test", max_results=1))
        console.print("✓ [green]Web Search (DDGS) accessible[/green]")
    except Exception as e:
        console.print(f"✗ [red]Web Search (DDGS) error: {e}[/red]")
        
@app.command()
def debug_lead(lead_id: int = typer.Argument(..., help="ID of the lead to audit")):
    """Audit a specific candidate processing pipeline."""
    from ssp.core.database import engine
    from sqlmodel import Session
    from ssp.core.models import Candidate
    
    with Session(engine) as session:
        cand = session.get(Candidate, lead_id)
        if not cand:
            console.print(f"[red]Lead {lead_id} not found.[/red]")
            return
            
        console.print("[bold]SOURCE DATA[/bold]")
        console.print("────────────")
        console.print(f"Source: {cand.source}")
        console.print(f"URL: {cand.source_url}")
        console.print(f"Timestamp: {cand.published_at or 'Unknown'} ({cand.timestamp_confidence or 'none'})")
        console.print("\n[bold]NORMALIZED[/bold]")
        console.print("────────────")
        console.print(f"Title: {cand.title}")
        console.print(f"Body: {cand.content[:200]}...")
        console.print(f"Event: {cand.event_type}")
        console.print("\n[bold]FILTERS & SCORING[/bold]")
        console.print("────────────")
        console.print(f"Garbage Filtered: {'Yes' if cand.garbage_filtered else 'No'}")
        console.print(f"Triage Relevant: {cand.triage_relevant}")
        console.print(f"Qualification Status: {cand.qualification_status}")
        console.print(f"Score: {cand.opportunity_score}")
        console.print("\n[bold]FINAL[/bold]")
        console.print("────────────")
        console.print(cand.qualification_status or ("REJECTED" if cand.garbage_filtered or not cand.triage_relevant else "PENDING"))
        
@app.command(name="tui")
def run_tui():
    """Launch the interactive Text User Interface (TUI)."""
    from ssp.ui.tui import SSPHunterApp
    init_db()
    tui_app = SSPHunterApp()
    tui_app.run()

if __name__ == "__main__":
    app()
