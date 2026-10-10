import httpx
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

class SearchEngineCore:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
            timeout=8.0,
            follow_redirects=True
        )

    def _rank_results(self, query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranking Algorithm: Title match weight (3x), snippet match weight (1x),
        exact phrase match bonus (5x).
        """
        terms = [re.escape(w.lower()) for w in query.split() if len(w) > 1]
        if not terms:
            return items

        for item in items:
            score = 0.0
            title = item.get("title", "").lower()
            snippet = item.get("snippet", "").lower()

            # Exact phrase match bonus
            if query.lower() in title:
                score += 5.0
            if query.lower() in snippet:
                score += 2.0

            # Term frequency & position
            for term in terms:
                title_matches = len(re.findall(r'\b' + term + r'\b', title))
                snippet_matches = len(re.findall(r'\b' + term + r'\b', snippet))
                score += (title_matches * 3.0) + (snippet_matches * 1.0)

            item["relevance_score"] = round(score, 2)

        return sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)

    async def execute_search(self, query: str) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        instant_answer = None

        encoded_q = quote_plus(query)

        # 1. Primary Source: DuckDuckGo Instant Answer API
        try:
            ddg_api_url = f"https://api.duckduckgo.com/?q={encoded_q}&format=json&no_html=1&skip_disambig=1"
            res = await self.client.get(ddg_api_url)
            if res.status_code == 200:
                data = res.json()
                
                # Check for direct knowledge graph / abstract
                if data.get("AbstractText"):
                    instant_answer = {
                        "heading": data.get("Heading", query),
                        "text": data.get("AbstractText"),
                        "source": data.get("AbstractSource"),
                        "url": data.get("AbstractURL"),
                        "image": data.get("Image") if data.get("Image") else None
                    }

                # Related topics extraction
                for topic in data.get("RelatedTopics", []):
                    if "Text" in topic and "FirstURL" in topic:
                        parts = topic["Text"].split(" - ", 1)
                        title = parts[0] if len(parts) > 1 else topic["Text"][:60]
                        snippet = parts[1] if len(parts) > 1 else topic["Text"]
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": topic["FirstURL"]
                        })
        except Exception:
            pass

        # 2. Live Web Fallback (HTML Scraping for real-time live web index)
        if len(results) < 5:
            try:
                html_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
                html_res = await self.client.get(html_url)
                if html_res.status_code == 200:
                    soup = BeautifulSoup(html_res.text, "html.parser")
                    links = soup.select(".result")
                    for elem in links[:10]:
                        title_tag = elem.select_one(".result__title .result__url") or elem.select_one(".result__title")
                        snippet_tag = elem.select_one(".result__snippet")
                        url_tag = elem.select_one(".result__url")

                        if title_tag and snippet_tag:
                            link = title_tag.get("href", "")
                            if link.startswith("/l/?uddg="):
                                link = link.split("uddg=")[1].split("&")[0]
                                link = httpx.URL(link).human_repr()

                            results.append({
                                "title": title_tag.get_text(strip=True),
                                "snippet": snippet_tag.get_text(strip=True),
                                "url": link or (url_tag.get_text(strip=True) if url_tag else "https://google.com")
                            })
            except Exception:
                pass

        # Rank and deduplicate
        seen_urls = set()
        deduped = []
        for r in results:
            if r["url"] not in seen_urls and r["url"].startswith("http"):
                seen_urls.add(r["url"])
                deduped.append(r)

        ranked_results = self._rank_results(query, deduped)

        return {
            "query": query,
            "total": len(ranked_results),
            "instant_answer": instant_answer,
            "results": ranked_results
        }
