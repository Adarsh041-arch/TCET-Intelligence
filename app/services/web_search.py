import requests


class WebSearchService:
    def search(self, query: str, api_key: str) -> dict:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "include_images": True,
            "max_results": 5,
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            answer = data.get("answer", "")
            images = data.get("images", [])

            # Safely handle image urls which might be strings or objects
            image_urls = []
            for img in images:
                if isinstance(img, dict) and img.get("url"):
                    image_urls.append(img["url"])
                elif isinstance(img, str):
                    image_urls.append(img)

            if not results and not answer:
                return {
                    "context": "No web search results found.",
                    "sources": [],
                    "images": []
                }
            output = ""
            if answer:
                output += f"Summary: {answer}\n\n"
            if results:
                output += "Search Results:\n"
                for i, r in enumerate(results[:5], 1):
                    title = r.get("title", "Untitled")
                    snippet = r.get("content", "")
                    src_url = r.get("url", "")
                    output += f"{i}. {title}\n   {snippet}\n   Source: {src_url}\n\n"
            
            sources = []
            for r in results:
                sources.append({
                    "title": r.get("title", "Untitled"),
                    "content": r.get("content", ""),
                    "url": r.get("url", "")
                })

            return {
                "context": output.strip(),
                "sources": sources,
                "images": image_urls
            }
        except requests.Timeout:
            return {
                "context": "Web search timed out.",
                "sources": [],
                "images": []
            }
        except Exception as e:
            return {
                "context": f"Web search error: {e}",
                "sources": [],
                "images": []
            }


web_search_service = WebSearchService()
