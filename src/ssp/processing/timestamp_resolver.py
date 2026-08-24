import httpx
from bs4 import BeautifulSoup
import json
from ssp.core.models import Candidate
import dateutil.parser
from rich.console import Console
from datetime import timezone

console = Console()

class TimestampResolver:
    @staticmethod
    async def resolve(candidate: Candidate, verbose: bool = False) -> Candidate:
        if candidate.published_at is not None:
            candidate.timestamp_confidence = "verified_platform"
            return candidate
            
        if not candidate.source_url:
            candidate.timestamp_confidence = "unknown"
            return candidate
            
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(candidate.source_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
                if resp.status_code != 200:
                    candidate.timestamp_confidence = "unknown"
                    return candidate
                    
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")
                
                # Try OpenGraph / Meta tags
                meta_date = soup.find("meta", {"property": "article:published_time"}) or \
                            soup.find("meta", {"itemprop": "datePublished"}) or \
                            soup.find("meta", {"name": "pubdate"})
                            
                if meta_date and meta_date.get("content"):
                    try:
                        dt = dateutil.parser.isoparse(meta_date["content"])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        candidate.published_at = dt
                        candidate.timestamp_confidence = "structured_metadata"
                        if verbose: console.print(f"[dim]Resolved timestamp for {candidate.title} via meta tag: {candidate.published_at}[/dim]")
                        return candidate
                    except Exception:
                        pass
                
                # Try JSON-LD
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string)
                        
                        # Handle case where JSON-LD is a list of objects
                        if isinstance(data, list):
                            objects = data
                        elif isinstance(data, dict):
                            objects = [data]
                            if "@graph" in data:
                                objects.extend(data["@graph"])
                        else:
                            continue
                            
                        for obj in objects:
                            if not isinstance(obj, dict): continue
                            date_str = obj.get("datePublished") or obj.get("uploadDate") or obj.get("dateCreated")
                            if date_str:
                                dt = dateutil.parser.isoparse(date_str)
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                candidate.published_at = dt
                                candidate.timestamp_confidence = "structured_metadata"
                                if verbose: console.print(f"[dim]Resolved timestamp for {candidate.title} via JSON-LD: {candidate.published_at}[/dim]")
                                return candidate
                    except Exception:
                        continue
                        
        except Exception as e:
            if verbose: console.print(f"[dim]Failed to resolve timestamp for {candidate.title}: {e}[/dim]")
            
        candidate.timestamp_confidence = "unknown"
        return candidate
