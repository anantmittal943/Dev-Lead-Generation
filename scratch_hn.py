import urllib.parse
import requests

queries = ["built with cursor", "built with lovable", "vibe coded", "ai generated"]
for query in queries:
    url1 = f"http://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}&tags=story"
    data = requests.get(url1).json()
    print(f"Query '{query}' hits:", data.get('nbHits'))
