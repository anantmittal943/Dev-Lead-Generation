import sys
import typer
import asyncio
from rich.console import Console

# Force UTF-8 encoding for Windows terminals to prevent charmap errors with checkmarks
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from rich.panel import Panel
from ssp.core.database import init_db

app = typer.Typer(
    help="SSP HUNTER - Engineering Opportunity Intelligence",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

@app.command()
def hunt(
    niche: str = typer.Argument(..., help="Niche to hunt for: 'ai-production', 'takeover'"),
    min_score: int = typer.Option(60, help="Minimum deterministic score to send to Groq"),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose output")
):
    """Discover new opportunities."""
    console.print(Panel(f"Running {niche.upper()} hunt...", title="SSP HUNTER", border_style="cyan"))
    init_db() # Ensure DB is initialized
    
    from ssp.services.hunt_service import HuntService
    service = HuntService()
    
    # Run async function
    asyncio.run(service.execute_hunt(niche, min_score, verbose))

@app.command()
def leads(
    niche: str = typer.Option(None, help="Filter by niche"),
    min_score: int = typer.Option(None, help="Filter by minimum score"),
    status: str = typer.Option(None, help="Filter by status")
):
    """Browse saved leads."""
    from ssp.core.database import engine
    from sqlmodel import Session, select
    from ssp.core.models import Lead
    from rich.table import Table
    
    with Session(engine) as session:
        query = select(Lead)
        if niche: query = query.where(Lead.niche == niche)
        if min_score: query = query.where(Lead.deterministic_score >= min_score)
        if status: query = query.where(Lead.status == status)
        
        results = session.exec(query).all()
        
        table = Table(title="SSP Hunter Leads")
        table.add_column("ID", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Niche", style="magenta")
        table.add_column("Title", style="white")
        table.add_column("Source", style="yellow")
        table.add_column("Verdict", style="blue")
        
        for lead in results:
            table.add_row(
                str(lead.id),
                str(lead.deterministic_score),
                lead.niche,
                lead.title[:50] + ("..." if len(lead.title)>50 else ""),
                lead.source,
                lead.llm_status or "UNRATED"
            )
            
        console.print(table)

@app.command()
def review():
    """Review and label candidates."""
    console.print("Interactive review mode is under construction.")

@app.command()
def queries():
    """Manage search intelligence."""
    console.print("Query management is under construction.")

@app.command()
def stats():
    """Analyze source/query performance."""
    console.print("Stats are under construction.")

@app.command()
def export():
    """Export qualified leads."""
    console.print("Export is under construction.")

@app.command()
def config():
    """Configure the application."""
    from ssp.core.config import settings
    console.print("[bold green]Configuration Loaded[/bold green]")
    console.print(f"Groq API Key: {'[green]✓ Configured[/green]' if settings.GROQ_API_KEY else '[red]✗ Missing[/red]'}")
    console.print(f"Reddit User Agent: {'[green]✓ Configured[/green]' if settings.REDDIT_USER_AGENT else '[red]✗ Missing[/red]'}")
    console.print(f"Database URL: {settings.DATABASE_URL}")

if __name__ == "__main__":
    app()
