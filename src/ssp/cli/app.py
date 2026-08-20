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
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not save to database")
):
    """Discover new opportunities via Event Intelligence."""
    console.print(Panel(f"Running {niche.upper()} event hunt", title="SSP HUNTER", border_style="cyan"))
    
    if not dry_run:
        init_db()
    
    from ssp.services.hunt_service import HuntService
    service = HuntService()
    
    try:
        asyncio.run(service.execute_hunt(niche, verbose=verbose, limit=limit, source=source, dry_run=dry_run))
    finally:
        from ssp.core.database import engine
        engine.dispose()

@app.command()
def leads(
    niche: str = typer.Option(None, help="Filter by niche"),
    status: str = typer.Option(None, help="Filter by status (HOT, WARM, WATCH)")
):
    """Browse saved leads."""
    from ssp.core.database import engine
    from sqlmodel import Session, select
    from ssp.core.models import Candidate
    from rich.table import Table
    
    with Session(engine) as session:
        query = select(Candidate)
        if niche: query = query.where(Candidate.niche == niche)
        if status: query = query.where(Candidate.qualification_status == status)
        
        results = session.exec(query).all()
        
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

if __name__ == "__main__":
    app()
