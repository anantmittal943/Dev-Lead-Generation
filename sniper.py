import os
import re
import csv
import json
import time
import sqlite3
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize Environment & UI
load_dotenv()
console = Console()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ssp_cli_ingestion:v2.0 (by /u/YOUR_USERNAME)")

if not GROQ_API_KEY:
    console.print("[bold red]Error: GROQ_API_KEY not found in environment variables.[/bold red]")
    exit(1)

# ==========================================
# 1. DATABASE DEDUPLICATION
# ==========================================
DB_FILE = "leads.db"
CSV_FILE = "qualified_leads.csv"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_leads (url TEXT PRIMARY KEY)''')
    conn.commit()
    return conn

def is_processed(conn, url):
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_leads WHERE url = ?', (url,))
    return c.fetchone() is not None

def mark_processed(conn, url):
    c = conn.cursor()
    c.execute('INSERT INTO processed_leads (url) VALUES (?)', (url,))
    conn.commit()

# ==========================================
# 2. NICHE DEFINITIONS & REGEX & PROMPTS
# ==========================================

NICHES = {
    "ai-production": {
        "title": "AI-Generated App -> Production",
        "reddit_subs": "SaaS+startups+Entrepreneur+indiehackers+webdev+SideProject",
        "reddit_regex": [
            re.compile(r'(?i)\b(cursor|lovable|bolt|v0|replit|ai generated|vibe coded|prototype)\b'),
            re.compile(r'(?i)\b(production|deploy|crash|security|scale|database|bug|help|issue|broken)\b')
        ],
        "hn_queries": ["built with cursor", "built with lovable", "vibe coded", "ai generated"],
        "ddg_queries": [
            'site:linkedin.com/posts "built with cursor" "deploy"',
            'site:linkedin.com/posts "built with lovable" "production"',
            'site:linkedin.com/posts "ai generated" "bug"'
        ],
        "system_prompt": """You are a ruthless B2B lead qualifier for a premium software engineering consultancy. 
Read the provided lead snippet.

PASS CRITERIA (Must meet BOTH):
1. The user built an app/MVP using an AI tool (Cursor, Lovable, Bolt, etc.) or is discussing rapid AI prototyping.
2. They are facing production, scaling, deployment, or technical debt issues and need professional engineering help.

FAIL CRITERIA: Hobbyists, $0 budget, students, or just showcasing an app without pain points.

Output strictly valid JSON with no markdown blocks:
{"status": "PASS" or "FAIL", "reason": "Short explanation", "pain_point_summary": "5 words max or empty"}"""
    },
    "takeover": {
        "title": "Abandoned Codebase Rescue",
        "reddit_subs": "SaaS+startups+Entrepreneur+smallbusiness",
        "reddit_regex": [
            re.compile(r'(?i)\b(developer left|previous developer|agency left|agency fired|legacy codebase|take over|finish app|unmaintained|abandoned|inherit codebase)\b')
        ],
        "hn_queries": ["developer left", "take over codebase", "previous developer"],
        "ddg_queries": [
            'site:linkedin.com/posts "developer left"',
            'site:linkedin.com/posts "previous developer"',
            'site:linkedin.com/posts "take over" "codebase"'
        ],
        "system_prompt": """You are a ruthless B2B lead qualifier for a premium software engineering consultancy.
Read the provided lead snippet.

PASS CRITERIA (Must meet BOTH):
1. The user is a founder/business owner with an existing codebase/product.
2. Their previous developer/agency left, or they explicitly need someone to take over, rescue, or maintain the project.

FAIL CRITERIA: Developers asking for coding help, students, zero-budget equity offers.

Output strictly valid JSON with no markdown blocks:
{"status": "PASS" or "FAIL", "reason": "Short explanation", "pain_point_summary": "5 words max or empty"}"""
    }
}

# ==========================================
# 3. INGESTION ENGINES ($0 Cost)
# ==========================================

def fetch_reddit(niche_key):
    console.print("[cyan]Hunting on Reddit...[/cyan]")
    config = NICHES[niche_key]
    url = f"https://www.reddit.com/r/{config['reddit_subs']}/new.json?limit=100"
    headers = {"User-Agent": REDDIT_USER_AGENT}
    
    leads = []
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            console.print(f"[bold red]Reddit blocked the request (Status {resp.status_code}). Please update REDDIT_USER_AGENT in your .env file with your real username.[/bold red]")
            return leads
            
        data = resp.json()
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            post_url = f"https://www.reddit.com{p.get('permalink')}"
            title = p.get('title', '')
            body = p.get('selftext', '')
            author = p.get('author', '')
            content = f"{title}\n{body}"
            
            # Apply Regex pre-filter
            passed_regex = True
            for regex in config['reddit_regex']:
                if not regex.search(content):
                    passed_regex = False
                    break
                    
            if passed_regex:
                leads.append({
                    "source": "Reddit",
                    "url": post_url,
                    "author": author,
                    "title": title,
                    "content": content[:1500]
                })
    except Exception as e:
        console.print(f"[red]Reddit fetch error: {e}[/red]")
        
    return leads

def fetch_hn(niche_key):
    console.print("[cyan]Hunting on Hacker News...[/cyan]")
    config = NICHES[niche_key]
    leads = []
    
    for query in config['hn_queries']:
        url = f"http://hn.algolia.com/api/v1/search_by_date?query={requests.utils.quote(query)}&tags=story"
        try:
            resp = requests.get(url, timeout=10).json()
            for hit in resp.get('hits', []):
                post_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
                leads.append({
                    "source": "Hacker News",
                    "url": post_url,
                    "author": hit.get('author', 'unknown'),
                    "title": hit.get('title', ''),
                    "content": hit.get('story_text', '') or hit.get('title', '')
                })
        except Exception as e:
            pass
    return leads

def fetch_linkedin(niche_key):
    console.print("[cyan]Hunting on LinkedIn (via DuckDuckGo)...[/cyan]")
    config = NICHES[niche_key]
    leads = []
    ddgs = DDGS()
    
    for query in config['ddg_queries']:
        try:
            results = ddgs.text(query, max_results=10)
            for r in results:
                if "linkedin.com" in r.get('href', ''):
                    leads.append({
                        "source": "LinkedIn",
                        "url": r.get('href'),
                        "author": "LinkedIn User",
                        "title": r.get('title', ''),
                        "content": r.get('body', '')
                    })
            time.sleep(2)
        except Exception as e:
            console.print(f"[red]DDG fetch error: {e}[/red]")
            
    return leads

# ==========================================
# 4. GROQ QUALIFICATION ENGINE
# ==========================================

def evaluate_lead(client, lead, niche_key):
    system_prompt = NICHES[niche_key]['system_prompt']
    user_prompt = f"TITLE: {lead['title']}\n\nCONTENT/SNIPPET:\n{lead['content']}"
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.0
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {"status": "FAIL", "reason": f"API Error: {str(e)}"}

# ==========================================
# 5. OUTPUT & MAIN LOOP
# ==========================================

def save_to_csv(lead_data):
    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Niche", "Source", "Author", "URL", "Pain_Point", "Reason"])
            writer.writerow([
                lead_data['timestamp'],
                lead_data['niche'],
                lead_data['source'],
                lead_data['author'],
                lead_data['url'],
                lead_data['pain_point'],
                lead_data['reason']
            ])
    except Exception as e:
        console.print(f"[bold red]Failed to write to CSV: {e}[/bold red]")

def print_lead(lead_data):
    table = Table(title=f"🔥 QUALIFIED LEAD: {lead_data['niche'].upper()}", style="green", show_header=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Details", style="white")

    table.add_row("Source:", lead_data['source'])
    table.add_row("Author:", lead_data['author'])
    table.add_row("URL:", lead_data['url'])
    table.add_row("Pain Point:", lead_data['pain_point'])
    table.add_row("", "")
    table.add_row("Reason:", lead_data['reason'])
    
    panel = Panel(table, expand=False, border_style="yellow")
    console.print(panel)

def hunt(niche_key, debug=False):
    console.print(Panel(f"Starting Sniper Hunt\nNiche: [bold green]{NICHES[niche_key]['title']}[/bold green]", expand=False))
    
    conn = init_db()
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
    
    all_leads = []
    all_leads.extend(fetch_reddit(niche_key))
    all_leads.extend(fetch_hn(niche_key))
    all_leads.extend(fetch_linkedin(niche_key))
    
    console.print(f"[dim]Total raw leads fetched matching basic queries: {len(all_leads)}[/dim]")
    
    processed_count = 0
    qualified_count = 0
    
    for lead in all_leads:
        if is_processed(conn, lead['url']):
            continue
            
        eval_result = evaluate_lead(client, lead, niche_key)
        
        if eval_result.get("status") == "PASS":
            lead_data = {
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "niche": niche_key,
                "source": lead['source'],
                "author": lead['author'],
                "url": lead['url'],
                "pain_point": eval_result.get("pain_point_summary", ""),
                "reason": eval_result.get("reason", "")
            }
            save_to_csv(lead_data)
            print_lead(lead_data)
            qualified_count += 1
        elif debug:
            reason = eval_result.get("reason", "No reason provided")
            console.print(f"[dim][REJECTED] {lead['source']} | {lead['url']}\nReason: {reason}[/dim]")
            
        mark_processed(conn, lead['url'])
        processed_count += 1
        
    conn.close()
    console.print(f"\n[bold green]Hunt Complete![/bold green] Processed {processed_count} new leads. Found {qualified_count} qualified leads.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSP Sniper - High Intent Lead Generation CLI")
    parser.add_argument("command", choices=["hunt"], help="Command to execute")
    parser.add_argument("--niche", choices=["ai-production", "takeover"], required=True, help="Target niche to hunt for")
    parser.add_argument("--debug", action="store_true", help="Print reasons why leads were rejected")
    
    args = parser.parse_args()
    
    if args.command == "hunt":
        hunt(args.niche, args.debug)
