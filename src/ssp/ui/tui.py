import asyncio
from typing import List, Dict, Any
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, DataTable, Markdown, Button, 
    OptionList, Input, Switch, Label, RichLog, Select, TabbedContent, TabPane
)
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual.worker import Worker, WorkerState
from textual import work
from rich.text import Text
from rich.console import Console

from sqlmodel import Session, select
from ssp.core.database import engine
from ssp.core.models import Candidate
from ssp.core.config import settings
from ssp.events.registry import EVENT_REGISTRY
from ssp.services.hunt_service import HuntService
import ssp.services.hunt_service as hunt_service_module

TUI_CSS = """
Screen {
    layout: vertical;
}

TabbedContent {
    height: 1fr;
}

#leads-container {
    height: 1fr;
    layout: horizontal;
}

#leads-table-container {
    width: 60%;
    height: 1fr;
    border-right: solid $primary;
}

#leads-table {
    width: 100%;
    height: 1fr;
}

#leads-controls {
    height: auto;
    padding: 1;
}

#btn-export-csv {
    width: auto;
    margin-top: 0;
}

#lead-details-scroll {
    width: 40%;
    height: 1fr;
    background: $panel;
}

#lead-details {
    padding: 1 2;
}

#hunt-container {
    height: 1fr;
    layout: horizontal;
}

#hunt-controls {
    width: 35%;
    height: 1fr;
    padding: 1 2;
    border-right: solid $primary;
}


#hunt-log {
    width: 65%;
    height: 1fr;
    background: $surface;
}

.control-group {
    margin-bottom: 2;
    height: auto;
}

.control-label {
    margin-bottom: 1;
    text-style: bold;
}

Button {
    width: 100%;
    margin-top: 2;
}

#config-container {
    padding: 2 4;
}
"""

class SSPHunterApp(App):
    """SSP Hunter Text User Interface."""
    
    CSS = TUI_CSS
    TITLE = "SSP Hunter"
    SUB_TITLE = "Engineering Opportunity Intelligence"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_leads", "Refresh Leads"),
        Binding("d", "toggle_dark", "Toggle Dark Mode")
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tab-leads"):
            with TabPane("Leads", id="tab-leads"):
                with Horizontal(id="leads-container"):
                    with Vertical(id="leads-table-container"):
                        with Horizontal(id="leads-controls"):
                            yield Button("Export CSV", id="btn-export-csv", variant="success")
                        yield DataTable(id="leads-table", cursor_type="row")
                    with VerticalScroll(id="lead-details-scroll"):
                        yield Markdown("Select a lead to view details.", id="lead-details")
            
            with TabPane("Hunt", id="tab-hunt"):
                with Horizontal(id="hunt-container"):
                    with Vertical(id="hunt-controls"):
                        yield Label("Niche", classes="control-label")
                        yield Select(
                            ((k, k) for k in EVENT_REGISTRY.keys()),
                            id="hunt-niche",
                            prompt="Select Niche"
                        )
                        
                        yield Label("Source", classes="control-label")
                        yield Select(
                            (("All", ""), ("Reddit", "reddit"), ("Hacker News", "hn"), ("Web", "web")),
                            id="hunt-source",
                            prompt="Select Source"
                        )
                        
                        yield Label("Limit (Queries)", classes="control-label")
                        yield Input(placeholder="e.g. 5 (Leave blank for all)", id="hunt-limit")
                        
                        yield Label("Max Age (Days)", classes="control-label")
                        yield Input(value="7", id="hunt-maxage")
                        
                        yield Horizontal(
                            Label("Verbose Output", classes="control-label"),
                            Switch(id="hunt-verbose"),
                            classes="control-group"
                        )
                        
                        yield Horizontal(
                            Label("Dry Run (Don't save)", classes="control-label"),
                            Switch(id="hunt-dryrun"),
                            classes="control-group"
                        )
                        
                        yield Button("Execute Hunt", variant="primary", id="btn-hunt")
                    
                    yield RichLog(id="hunt-log", highlight=True, markup=True)
            
            with TabPane("Config", id="tab-config"):
                with Vertical(id="config-container"):
                    yield Markdown(self._get_config_markdown(), id="config-md")
                    
        yield Footer()
        
    def _get_config_markdown(self) -> str:
        db_url = settings.DATABASE_URL
        groq_ok = "✅ Configured" if settings.GROQ_API_KEY else "❌ Missing"
        reddit_ok = "✅ Configured" if settings.REDDIT_USER_AGENT else "❌ Missing"
        
        return f"""# Configuration
        
**Database URL:** `{db_url}`
**Groq API Key:** {groq_ok}
**Reddit User Agent:** {reddit_ok}

## Available Niches
{chr(10).join(f"- **{k}**: {len(v.events)} events configured" for k, v in EVENT_REGISTRY.items())}
"""

    def on_mount(self) -> None:
        """Initialize data on mount."""
        table = self.query_one("#leads-table", DataTable)
        table.add_columns("ID", "Score", "Niche", "Title", "Status")
        self.action_refresh_leads()
        
    def action_refresh_leads(self) -> None:
        """Load leads from the database."""
        table = self.query_one("#leads-table", DataTable)
        table.clear()
        
        with Session(engine) as session:
            candidates = session.exec(select(Candidate).order_by(Candidate.id.desc())).all()
            
            for cand in candidates:
                score = f"{cand.opportunity_score:.1f}" if cand.opportunity_score else "N/A"
                title = cand.title[:45] + "..." if cand.title and len(cand.title) > 45 else cand.title
                status = cand.qualification_status or "UNRATED"
                
                table.add_row(
                    str(cand.id),
                    score,
                    cand.niche,
                    title,
                    status,
                    key=str(cand.id)
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to show lead details."""
        row_key = event.row_key.value
        if not row_key:
            return
            
        with Session(engine) as session:
            cand = session.get(Candidate, int(row_key))
            if cand:
                md = self.query_one("#lead-details", Markdown)
                
                details = f"""# {cand.title}
                
**ID:** {cand.id} | **Niche:** {cand.niche} | **Status:** {cand.qualification_status}
**Score:** {cand.opportunity_score} | **Event Type:** {cand.event_type}
**Source:** [{cand.source}]({cand.source_url})
**Contact Info:** {cand.contact_info or "None found"}

## Content
{cand.content}

## Pain Point Summary
{cand.pain_point_summary or "N/A"}

## Triage Reason
{cand.triage_reason or "N/A"}
"""
                md.update(details)

    def action_export_csv(self) -> None:
        """Export leads to a CSV file."""
        import csv
        import os
        from datetime import datetime
        
        filename = f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with Session(engine) as session:
            results = session.exec(select(Candidate)).all()
            try:
                with open(filename, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Niche", "Title", "Status", "Score", "Event Type", "Source", "Source URL", "Contact Info", "Pain Point Summary", "Recommended Action"])
                    for cand in results:
                        writer.writerow([
                            cand.id, cand.niche, cand.title, cand.qualification_status, cand.opportunity_score,
                            cand.event_type, cand.source, cand.source_url, cand.contact_info,
                            cand.pain_point_summary, cand.recommended_action
                        ])
                self.notify(f"Successfully exported {len(results)} leads to {filename}")
            except Exception as e:
                self.notify(f"Failed to export: {e}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-export-csv":
            self.action_export_csv()
            return
            
        if event.button.id == "btn-hunt":
            niche_select = self.query_one("#hunt-niche", Select)
            if not niche_select.value or niche_select.value == Select.BLANK:
                self.query_one("#hunt-log", RichLog).write("[bold red]Please select a niche first.[/bold red]")
                return
                
            niche = str(niche_select.value)
            
            source_select = self.query_one("#hunt-source", Select)
            source = str(source_select.value) if source_select.value and source_select.value != Select.BLANK else None
            
            limit_val = self.query_one("#hunt-limit", Input).value
            limit = int(limit_val) if limit_val.isdigit() else None
            
            maxage_val = self.query_one("#hunt-maxage", Input).value
            max_age_days = int(maxage_val) if maxage_val.isdigit() else 7
            
            verbose = self.query_one("#hunt-verbose", Switch).value
            dry_run = self.query_one("#hunt-dryrun", Switch).value
            
            event.button.disabled = True
            log = self.query_one("#hunt-log", RichLog)
            log.clear()
            log.write(f"[bold cyan]Starting Hunt for '{niche}'...[/bold cyan]")
            
            self.run_hunt_worker(niche, source, limit, max_age_days, verbose, dry_run)

    @work(exclusive=True, thread=True)
    def run_hunt_worker(self, niche: str, source: str, limit: int, max_age_days: int, verbose: bool, dry_run: bool) -> None:
        """Run the hunt in a separate worker thread."""
        log = self.query_one("#hunt-log", RichLog)
        
        original_print = hunt_service_module.console.print
        
        def patched_print(*args, **kwargs):
            for arg in args:
                self.call_from_thread(log.write, arg)
                
        hunt_service_module.console.print = patched_print
        
        try:
            service = HuntService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                service.execute_hunt(niche=niche, verbose=verbose, limit=limit, source=source, max_age_days=max_age_days, dry_run=dry_run)
            )
        except Exception as e:
            self.call_from_thread(log.write, f"[bold red]Error during hunt: {e}[/bold red]")
        finally:
            hunt_service_module.console.print = original_print
            def reenable():
                self.query_one("#btn-hunt", Button).disabled = False
                self.action_refresh_leads()
                log.write("[bold green]Hunt Complete![/bold green]")
            self.call_from_thread(reenable)
            
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "light" if self.theme == "dark" else "dark"

if __name__ == "__main__":
    app = SSPHunterApp()
    app.run()
