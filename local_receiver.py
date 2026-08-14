import os
import csv
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from rich.console import Console
from rich.table import Table

console = Console()

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            # 1. Save to CSV
            csv_file = "qualified_leads.csv"
            file_exists = os.path.isfile(csv_file)
                
            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Subreddit", "Author", "Title", "Post_URL", "Pain_Point", "Reason"])
                writer.writerow([
                    data.get('timestamp'), 
                    data.get('subreddit'), 
                    data.get('author'), 
                    data.get('title'),
                    data.get('post_url'), 
                    data.get('pain_point'), 
                    data.get('reason')
                ])
                
            # 2. Print to Terminal via Rich
            table = Table(title="🎯 Qualified Lead Snipped (Via Devvit)!", style="green")
            table.add_column("Field", style="cyan", no_wrap=True)
            table.add_column("Details", style="white")

            table.add_row("Title", data.get('title', ''))
            table.add_row("Subreddit", data.get('subreddit', ''))
            table.add_row("Author", f"/u/{data.get('author', '')}")
            table.add_row("URL", data.get('post_url', ''))
            table.add_row("Pain Point", data.get('pain_point', ''))
            table.add_row("LLM Reason", data.get('reason', ''))

            console.print(table)
            print() # Spacer
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        
        except Exception as e:
            console.print(f"[bold red]Error processing webhook: {e}[/bold red]")
            self.send_response(500)
            self.end_headers()

    # Suppress default HTTP logging to keep the terminal clean
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    PORT = 8080
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    console.print(f"[bold green][*] SSP Sniper Local Receiver active on port {PORT}[/bold green]")
    console.print("[dim]Waiting for Devvit webhooks. Use ngrok (e.g. `ngrok http 8080`) to expose this to the internet![/dim]\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[bold red][*] Shutting down receiver.[/bold red]")
