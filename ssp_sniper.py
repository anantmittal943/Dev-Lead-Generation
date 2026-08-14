import os
import re
import json
import sqlite3
import argparse
import requests
import praw
from openai import OpenAI
from dotenv import load_dotenv
import time
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "script:ssp-sniper:v1.0 (by /u/YOUR_USERNAME)")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Regex Clusters
CLUSTER_1_HIRING_INTENT = re.compile(r'(?i)\b(hiring|looking for a dev|need a developer|technical cofounder|freelance|agency|dev shop)\b')
CLUSTER_2_TECHNICAL_PAIN = re.compile(r'(?i)\b(app keeps crashing|slow down|database migration|offshore team failed|spaghetti code|AWS bill|scaling issues|technical debt|UI jank|refactor)\b')

LLM_SYSTEM_PROMPT = """
You are a ruthless B2B lead qualifier for a premium software engineering consultancy. 
Read the provided Reddit post. 

PASS CRITERIA (Must meet BOTH): 
1. The user is a founder, business owner, or project lead with an actual budget.
2. They have a concrete technical problem, need an MVP built, or are actively seeking high-quality development help. 

FAIL CRITERIA (If ANY of these apply, reject immediately):
1. It is a student asking for homework/project help.
2. It is another developer asking a coding/debugging question.
3. It is an "idea guy" with zero budget asking someone to build a product for equity only.
4. They explicitly state they are looking for "cheap" labor or a $5/hr offshore dev. 

Output strictly valid JSON with no markdown formatting:
{
  "status": "PASS" or "FAIL",
  "reason": "One sentence explaining why it passed or failed.",
  "pain_point_summary": "If PASS, summarize their technical problem in 5 words or less. If FAIL, leave empty."
}
"""

def init_db(db_path: str = "leads.db") -> sqlite3.Connection:
    """Initialize the local SQLite database to prevent duplicates."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_posts (post_id TEXT PRIMARY KEY)''')
    conn.commit()
    return conn

def is_processed(conn: sqlite3.Connection, post_id: str) -> bool:
    """Check if a post has already been processed."""
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_posts WHERE post_id = ?', (post_id,))
    return c.fetchone() is not None

def mark_processed(conn: sqlite3.Connection, post_id: str):
    """Mark a post as processed in the database."""
    c = conn.cursor()
    c.execute('INSERT INTO processed_posts (post_id) VALUES (?)', (post_id,))
    conn.commit()

def passes_regex(title: str, body: str) -> bool:
    """Check if the post matches either hiring intent or technical pain keywords."""
    content = f"{title}\n{body}"
    if CLUSTER_1_HIRING_INTENT.search(content):
        return True
    if CLUSTER_2_TECHNICAL_PAIN.search(content):
        return True
    return False

def qualify_lead(title: str, body: str) -> Optional[Dict[str, str]]:
    """Send post to OpenAI to qualify the lead."""
    if not OPENAI_API_KEY:
        print("[!] OPENAI_API_KEY not set. Skipping LLM qualification.")
        return None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        user_prompt = f"TITLE: {title}\n\nBODY:\n{body}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT.strip()},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[!] LLM API error: {e}")
        return None

def send_discord_alert(post: Any, llm_result: Dict[str, str]):
    """Send a rich embed webhook to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("[!] DISCORD_WEBHOOK_URL not set. Cannot send alert.")
        return

    author_url = f"https://reddit.com/user/{post.author.name}" if post.author else "https://reddit.com"
    author_name = post.author.name if post.author else "[deleted]"
    snippet = post.selftext[:200] + ("..." if len(post.selftext) > 200 else "")
    
    embed = {
        "title": post.title,
        "url": f"https://reddit.com{post.permalink}",
        "color": 0x00FF00, # Green for pass
        "author": {
            "name": f"/u/{author_name}",
            "url": author_url
        },
        "fields": [
            {"name": "Subreddit", "value": f"r/{post.subreddit.display_name}", "inline": True},
            {"name": "Pain Point", "value": llm_result.get("pain_point_summary", "N/A"), "inline": True},
            {"name": "Snippet", "value": snippet if snippet.strip() else "*No body text*", "inline": False},
            {"name": "LLM Reason", "value": llm_result.get("reason", ""), "inline": False}
        ],
        "footer": {"text": "🎯 SSP Sniper System"}
    }
    
    payload = {"embeds": [embed]}
    
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        res.raise_for_status()
        print(f"[+] Alert sent to Discord for post: {post.id}")
    except Exception as e:
        print(f"[!] Discord Webhook error: {e}")

def get_reddit_instance() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

def process_post(post: Any, conn: sqlite3.Connection):
    """Core logic to process a single Reddit post."""
    if is_processed(conn, post.id):
        return

    title = post.title
    body = post.selftext

    # 1. Regex Pre-filter
    if not passes_regex(title, body):
        mark_processed(conn, post.id)
        return

    print(f"[*] Post {post.id} passed regex. Sending to LLM...")

    # 2. LLM Qualification
    llm_result = qualify_lead(title, body)
    if llm_result:
        status = llm_result.get("status", "FAIL")
        
        if status == "PASS":
            print(f"[+] Post {post.id} QUALIFIED. Dispatching alert...")
            send_discord_alert(post, llm_result)
        else:
            print(f"[-] Post {post.id} REJECTED. Reason: {llm_result.get('reason')}")

    # 3. Mark processed
    mark_processed(conn, post.id)

def run_batch(subreddits: str, limit: int):
    """Fetch the latest N posts from the subreddits and process them."""
    reddit = get_reddit_instance()
    conn = init_db()
    
    subreddit_multi = "+".join([s.strip() for s in subreddits.split(',')])
    print(f"[*] Running BATCH mode on r/{subreddit_multi} (Limit: {limit})")
    
    # praw natively adheres to rate limits, but we fetch up to `limit` posts.
    subreddit = reddit.subreddit(subreddit_multi)
    for post in subreddit.new(limit=limit):
        process_post(post, conn)
        
    print("[*] Batch run complete.")

def run_stream(subreddits: str):
    """Continuously listen for new posts using PRAW's submission stream."""
    reddit = get_reddit_instance()
    conn = init_db()
    
    subreddit_multi = "+".join([s.strip() for s in subreddits.split(',')])
    print(f"[*] Running STREAM mode on r/{subreddit_multi}...")
    
    subreddit = reddit.subreddit(subreddit_multi)
    
    # pause_after=None keeps blocking indefinitely. PRAW auto-handles the standard rate limits.
    try:
        for post in subreddit.stream.submissions(skip_existing=True):
            process_post(post, conn)
    except KeyboardInterrupt:
        print("\n[*] Stream terminated by user.")
    except Exception as e:
        print(f"[!] Stream error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSP Sniper - Reddit Lead Generation CLI")
    parser.add_argument("mode", choices=["batch", "stream"], help="Mode of operation: 'batch' (fetch recent N) or 'stream' (continuous listen)")
    parser.add_argument("--subreddits", "-s", type=str, default="SaaS,startups,Entrepreneur,webdev,appideas,cofounder,smallbusiness", help="Comma-separated list of subreddits")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Number of posts to fetch per subreddit in batch mode")
    
    args = parser.parse_args()
    
    # Pre-flight checks
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        print("[!] Error: Reddit credentials missing in environment variables.")
        exit(1)
        
    if args.mode == "batch":
        run_batch(args.subreddits, args.limit)
    elif args.mode == "stream":
        run_stream(args.subreddits)
