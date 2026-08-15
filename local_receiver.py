import os
import csv
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

app = Flask(__name__)
console = Console()

RECEIVER_SECRET = os.getenv("RECEIVER_SECRET")
CSV_FILE = "qualified_leads.csv"

if not RECEIVER_SECRET:
    console.print("[bold red][!] RECEIVER_SECRET not found in environment. Please set it in .env[/bold red]")
    exit(1)

def is_duplicate(post_url: str) -> bool:
    """Checks if a post_url already exists in the CSV to prevent duplicates on retries."""
    if not os.path.isfile(CSV_FILE):
        return False
    try:
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Schema: Timestamp,Subreddit,Author,Post_URL,Pain_Point,Reason
            for row in reader:
                if len(row) > 3 and row[3] == post_url:
                    return True
    except Exception as e:
        console.print(f"[bold red]Error reading CSV for deduplication: {e}[/bold red]")
    return False

@app.route('/lead', methods=['POST'])
def receive_lead():
    # 1. Authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split(" ")[1]
    if token != RECEIVER_SECRET:
        return jsonify({"error": "Forbidden"}), 403

    # 2. Parse Payload
    data = request.json
    if not data:
        return jsonify({"error": "Bad Request: Empty JSON"}), 400

    timestamp = data.get('timestamp')
    subreddit = data.get('subreddit')
    author = data.get('author')
    post_url = data.get('post_url')
    title = data.get('title', '')
    pain_point = data.get('pain_point', '')
    reason = data.get('reason', '')

    if not post_url:
        return jsonify({"error": "Missing post_url"}), 400

    # 3. Defensive Deduplication
    if is_duplicate(post_url):
        console.print(f"[dim]Duplicate lead ignored: {post_url}[/dim]")
        return jsonify({"status": "ignored", "reason": "duplicate"}), 200

    # 4. Save to CSV
    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Subreddit", "Author", "Post_URL", "Pain_Point", "Reason"])
            writer.writerow([timestamp, subreddit, author, post_url, pain_point, reason])
    except Exception as e:
        console.print(f"[bold red][!] Error writing to CSV: {e}[/bold red]")
        return jsonify({"error": "Internal Server Error during CSV write"}), 500

    # 5. Terminal Output
    table = Table(title="🔥 QUALIFIED LEAD", style="green", show_header=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Details", style="white")

    table.add_row("Title:", title)
    table.add_row("Subreddit:", f"r/{subreddit}")
    table.add_row("Author:", author)
    table.add_row("Pain Point:", pain_point)
    table.add_row("", "")
    table.add_row("Reddit URL:", post_url)
    table.add_row("", "")
    table.add_row("Reason:", reason)
    
    panel = Panel(table, expand=False, border_style="yellow")
    console.print(panel)
    console.print("[bold green]✓ Lead saved to qualified_leads.csv[/bold green]\n")

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.getenv("RECEIVER_PORT", "8080"))
    console.print(f"[bold cyan]SSP Sniper Receiver[/bold cyan]")
    console.print(f"Listening on http://0.0.0.0:{port}")
    console.print("[dim]Waiting for qualified leads...[/dim]\n")
    # In production, use Waitress or Gunicorn, but Flask built-in is fine for local dev/tunnelling
    app.run(host='0.0.0.0', port=port)
