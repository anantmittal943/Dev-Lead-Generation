"""
Indie Hackers source adapter.

IH has no public API, so we scrape their server-rendered forum pages.
The pages are plain HTML — no JS wall, no CAPTCHA under light load.

Contact surface: every IH post links to /[username].  We set author_url
to that profile URL.  Users frequently list their Twitter/product URL on
their profile, but we surface the IH profile as the minimum contact point.

Rate limiting: 1 request per 2 seconds, max 3 pages per category pass.
This intentionally mimics normal human browsing speed.

Scraped paths (all public, no auth):
  /forum?sort=new                 — latest forum posts (any topic)
  /forum/post/[slug]              — individual post (for full content)
"""
import asyncio
import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus

import httpx
from bs4 import BeautifulSoup

from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

_BASE = "https://www.indiehackers.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# IH forum categories most relevant to our two niches
_CATEGORIES = [
    "/forum?sort=new",
    "/group/founders-of-saas-products?sort=new",
    "/group/growing-a-startup?sort=new",
]

# How many pages deep to scrape per category
_MAX_PAGES = 2
# Delay between requests (seconds)
_DELAY = 2.0


def _parse_relative_time(time_str: str) -> Optional[datetime]:
    """
    IH shows relative times like '3 hours ago', '2 days ago', '1 week ago'.
    Convert to approximate absolute UTC datetime.
    """
    if not time_str:
        return None
    now = time.time()
    time_str = time_str.lower().strip()

    patterns = [
        (r"(\d+)\s+second", 1),
        (r"(\d+)\s+minute", 60),
        (r"(\d+)\s+hour", 3600),
        (r"(\d+)\s+day", 86400),
        (r"(\d+)\s+week", 604800),
        (r"(\d+)\s+month", 2592000),
    ]
    for pattern, multiplier in patterns:
        m = re.search(pattern, time_str)
        if m:
            delta = int(m.group(1)) * multiplier
            return datetime.fromtimestamp(now - delta, tz=timezone.utc)
    return None


def _keywords_match(text: str, query: str) -> bool:
    """Return True if any meaningful word from the query appears in text."""
    text = text.lower()
    words = [w.strip('"\'').lower() for w in query.split() if len(w.strip('"\'')) > 3]
    return any(w in text for w in words)


class IndieHackersSource(BaseSource):
    """Source adapter for Indie Hackers forum via scraping."""

    async def search(
        self,
        queries: List[Dict[str, str]],
        max_age_days: int = 7,
        verbose: bool = False,
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        cutoff_ts = time.time() - (max_age_days * 24 * 3600)
        seen_urls: set = set()

        # We collect all forum posts once (not per-query) to avoid hammering IH.
        # Then we do keyword matching against the query list locally.
        raw_posts: List[dict] = []

        async with httpx.AsyncClient(
            timeout=20.0, headers=_HEADERS, follow_redirects=True
        ) as client:
            # --- Scrape forum listing pages ---
            for category_path in _CATEGORIES:
                for page in range(1, _MAX_PAGES + 1):
                    url = f"{_BASE}{category_path}" + (f"&page={page}" if page > 1 else "")
                    try:
                        if verbose:
                            console.print(f"[dim]IH scraping: {url}[/dim]")

                        resp = await client.get(url)
                        if resp.status_code != 200:
                            if verbose:
                                console.print(f"[red]IH HTTP {resp.status_code}: {url}[/red]")
                            break

                        soup = BeautifulSoup(resp.text, "html.parser")

                        # IH renders posts as <div class="feed-item"> or similar
                        # The selectors below target the stable structural patterns
                        post_cards = (
                            soup.select("div.feed-item")
                            or soup.select("div.post-preview")
                            or soup.select("li.post")
                            or soup.select("article")
                        )

                        if not post_cards:
                            if verbose:
                                console.print(f"[yellow]IH: no post cards found on {url} (layout may have changed)[/yellow]")
                            break

                        for card in post_cards:
                            # Title + post URL
                            title_tag = card.find("a", class_=re.compile(r"title|headline|post-link", re.I))
                            if not title_tag:
                                title_tag = card.find("h2") or card.find("h3") or card.find("a")
                            if not title_tag:
                                continue

                            post_title = title_tag.get_text(strip=True)
                            post_href = title_tag.get("href", "")
                            if not post_href.startswith("http"):
                                post_href = urljoin(_BASE, post_href)

                            if post_href in seen_urls:
                                continue

                            # Snippet / excerpt
                            snippet_tag = card.find(class_=re.compile(r"excerpt|preview|body|description", re.I))
                            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                            # Author
                            author_tag = card.find("a", class_=re.compile(r"user|author|username", re.I))
                            if not author_tag:
                                author_tag = card.find(attrs={"data-username": True})
                            username = ""
                            if author_tag:
                                username = (
                                    author_tag.get("data-username")
                                    or author_tag.get_text(strip=True).lstrip("@")
                                )
                            author_url = f"{_BASE}/{username}" if username else None

                            # Time
                            time_tag = card.find("time") or card.find(class_=re.compile(r"date|time|ago", re.I))
                            time_str = ""
                            if time_tag:
                                time_str = time_tag.get("datetime") or time_tag.get_text(strip=True)

                            published_at: Optional[datetime] = None
                            if time_str:
                                # Try ISO first (from <time datetime="...">)
                                try:
                                    published_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                                    if published_at.tzinfo is None:
                                        published_at = published_at.replace(tzinfo=timezone.utc)
                                except ValueError:
                                    published_at = _parse_relative_time(time_str)

                            if published_at and published_at.timestamp() < cutoff_ts:
                                continue

                            seen_urls.add(post_href)
                            raw_posts.append({
                                "title": post_title,
                                "url": post_href,
                                "snippet": snippet,
                                "author": username or "unknown",
                                "author_url": author_url,
                                "published_at": published_at,
                            })

                        await asyncio.sleep(_DELAY)

                    except Exception as e:
                        if verbose:
                            console.print(f"[red]IH scrape error ({url}): {e}[/red]")
                        break  # don't retry same category on error

        if verbose:
            console.print(f"\n[cyan]SOURCE: INDIE HACKERS[/cyan]")
            console.print(f"[green]RAW POSTS SCRAPED: {len(raw_posts)}[/green]")

        # --- Match scraped posts against each query ---
        for q_obj in queries:
            query: str = q_obj["query"]
            event_type: str = q_obj["event_type"]
            matched = 0

            for post in raw_posts:
                combined = f"{post['title']} {post['snippet']}"
                if not _keywords_match(combined, query):
                    continue

                contact_summary = (
                    f"IH profile: {post['author_url']}" if post["author_url"]
                    else "No contact surface found"
                )

                candidates.append(Candidate(
                    source="Indie Hackers",
                    source_url=post["url"],
                    title=post["title"],
                    content=post["snippet"],
                    content_type="SNIPPET_ONLY",
                    author=post["author"],
                    author_url=post["author_url"],
                    published_at=post["published_at"],
                    timestamp_confidence="approximate" if post["published_at"] else "unverified",
                    query=query,
                    event_type=event_type,
                    raw_metadata={
                        "ih_username": post["author"],
                        "contact_summary": contact_summary,
                    },
                ))
                matched += 1

            if verbose:
                console.print(f"[green]MATCHED (query='{query[:40]}'): {matched}[/green]")
                console.print("────────────────────────────")

        return candidates
