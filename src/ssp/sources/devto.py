"""
dev.to source adapter.

Uses the free, unauthenticated dev.to public API:
  - /api/articles?tag=<tag>&per_page=30&sort=latest
  - /api/articles/<id>  (for full body + author social links)

Contact surface: every dev.to article/comment has a user object with
twitter_username and github_username as first-class API fields.  We always
populate author_url and embed socials in raw_metadata so the qualifier
stage has something concrete to surface in contact_info.

No auth needed.  Rate limit is ~3 req/s which we respect with a 0.35s sleep.
"""
import asyncio
import httpx
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional

from ssp.sources.base import BaseSource
from ssp.core.models import Candidate
from rich.console import Console

console = Console()

_BASE = "https://dev.to/api"
_HEADERS = {
    "User-Agent": "ssp-hunter/1.0 (lead-gen research tool; contact: github.com/ssp-hunter)",
    "Accept": "application/json",
}

# Map broad query phrases to the most relevant dev.to tags
_TAG_MAP: Dict[str, List[str]] = {
    "default": ["startup", "saas", "webdev", "entrepreneur", "buildinpublic"],
    "ai": ["ai", "machinelearning", "llm", "gpt", "vibe"],
    "deployment": ["devops", "docker", "cloud", "aws", "deployment"],
    "hiring": ["hiring", "jobs", "freelance", "remotework"],
}


def _pick_tags(query: str) -> List[str]:
    """Return the most relevant tag list for a given query string."""
    q = query.lower()
    if any(w in q for w in ("ai", "cursor", "lovable", "bolt", "vibe", "llm", "gpt")):
        return _TAG_MAP["ai"] + _TAG_MAP["default"]
    if any(w in q for w in ("deploy", "production", "crash", "scale", "infra")):
        return _TAG_MAP["deployment"] + _TAG_MAP["default"]
    if any(w in q for w in ("hire", "freelance", "developer", "engineer", "cto")):
        return _TAG_MAP["hiring"] + _TAG_MAP["default"]
    return _TAG_MAP["default"]


def _build_contact(user: dict) -> tuple[Optional[str], str]:
    """Return (author_url, contact_summary) from a dev.to user object."""
    username = user.get("username", "")
    twitter = user.get("twitter_username", "")
    github = user.get("github_username", "")

    author_url = f"https://dev.to/{username}" if username else None

    parts = []
    if author_url:
        parts.append(f"dev.to profile: {author_url}")
    if twitter:
        parts.append(f"Twitter/X: @{twitter} (DM available)")
    if github:
        parts.append(f"GitHub: https://github.com/{github}")

    contact_summary = " | ".join(parts) if parts else "No contact surface found on dev.to profile"
    return author_url, contact_summary


class DevToSource(BaseSource):
    """Source adapter for dev.to articles via the public REST API."""

    async def search(
        self,
        queries: List[Dict[str, str]],
        max_age_days: int = 7,
        verbose: bool = False,
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        cutoff_ts = time.time() - (max_age_days * 24 * 3600)
        seen_ids: set = set()

        async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as client:
            for q_obj in queries:
                query: str = q_obj["query"]
                event_type: str = q_obj["event_type"]

                if verbose:
                    console.print(f"\n[cyan]SOURCE: DEV.TO[/cyan]")
                    console.print(f"[cyan]EVENT: {event_type}[/cyan]")
                    console.print(f"[cyan]QUERY: {query}[/cyan]")

                tags = _pick_tags(query)
                raw_found = 0

                for tag in tags[:3]:  # cap at 3 tags per query to stay within rate limits
                    try:
                        url = f"{_BASE}/articles?tag={tag}&per_page=30&sort=latest"
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            if verbose:
                                console.print(f"[red]DEV.TO HTTP {resp.status_code} for tag={tag}[/red]")
                            continue

                        articles = resp.json()
                        raw_found += len(articles)

                        for article in articles:
                            art_id = article.get("id")
                            if not art_id or art_id in seen_ids:
                                continue

                            # Date check — dev.to returns ISO 8601 published_at
                            pub_str = article.get("published_at") or article.get("created_at")
                            published_at: Optional[datetime] = None
                            if pub_str:
                                try:
                                    published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                                    if published_at.tzinfo is None:
                                        published_at = published_at.replace(tzinfo=timezone.utc)
                                    if published_at.timestamp() < cutoff_ts:
                                        continue
                                except Exception:
                                    pass  # freshness filter handles None gracefully

                            # Keyword relevance gate — only keep if any query word appears
                            title = article.get("title", "")
                            description = article.get("description", "") or ""
                            body_snippet = f"{title} {description}".lower()
                            # Accept if at least one meaningful query word matches
                            query_words = [w for w in query.split() if len(w) > 3]
                            if not any(w.lower().strip('"') in body_snippet for w in query_words):
                                continue

                            seen_ids.add(art_id)

                            # Build contact info from the article's user object
                            user = article.get("user", {})
                            author_url, contact_summary = _build_contact(user)
                            author = user.get("name") or user.get("username") or "unknown"

                            candidates.append(Candidate(
                                source="dev.to",
                                source_url=article.get("url") or f"https://dev.to/articles/{art_id}",
                                title=title,
                                content=description,  # full body fetched below if relevant
                                content_type="SNIPPET_ONLY",
                                author=author,
                                author_url=author_url,
                                published_at=published_at,
                                timestamp_confidence="verified_platform" if published_at else "unverified",
                                query=query,
                                event_type=event_type,
                                raw_metadata={
                                    "devto_id": art_id,
                                    "tag_used": tag,
                                    "twitter_username": user.get("twitter_username"),
                                    "github_username": user.get("github_username"),
                                    "devto_username": user.get("username"),
                                    "contact_summary": contact_summary,
                                    "positive_reactions_count": article.get("positive_reactions_count", 0),
                                    "comments_count": article.get("comments_count", 0),
                                },
                            ))

                        await asyncio.sleep(0.35)  # respect ~3 req/s rate limit

                    except Exception as e:
                        if verbose:
                            console.print(f"[red]DEV.TO error (tag={tag}): {e}[/red]")

                if verbose:
                    console.print(f"[green]RAW RESULTS: {raw_found}[/green]")
                    console.print(f"[green]NORMALIZED: {len([c for c in candidates if c.query == query])}[/green]")
                    console.print("────────────────────────────")

        return candidates
