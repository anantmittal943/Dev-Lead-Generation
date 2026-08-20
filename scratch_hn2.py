import asyncio
import httpx
import urllib.parse
from ssp.core.models import Lead

async def test():
    query = "developer left"
    url = f"http://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}&tags=story"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        print("Total hits:", len(data.get('hits', [])))
        for hit in data.get('hits', [])[:2]:
            try:
                lead = Lead(
                    niche="",
                    source="Hacker News",
                    source_id=f"hn_{hit['objectID']}",
                    title=hit.get('title', ''),
                    body=hit.get('story_text', '') or '',
                    author=hit.get('author', 'unknown'),
                    source_url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    content_type="full_content"
                )
                print("Successfully created Lead:", lead.title)
            except Exception as e:
                print("Failed to create Lead:", repr(e))

asyncio.run(test())
