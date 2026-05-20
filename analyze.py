import json
import os
import base64
import glob
import urllib.request
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        keyword = body.get('keyword', 'financial planning')

        # Search TikTok
        scrape_key = os.environ.get('SCRAPE_API_KEY')
        req = urllib.request.Request(
            f"https://api.scrapecreators.com/v1/tiktok/search/keyword?query={keyword}",
            headers={"x-api-key": scrape_key}
        )
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())

        videos = data.get('search_item_list', [])

        # Filter by views and likes
        filtered = []
        for item in videos:
            info = item.get('aweme_info', {})
            stats = info.get('statistics', {})
            views = stats.get('play_count', 0)
            likes = stats.get('digg_count', 0)
            if views >= 100000 and likes >= 2000:
                filtered.append({
                    'author': info.get('author', {}).get('nickname', ''),
                    'desc': info.get('desc', ''),
                    'views': views,
                    'likes': likes,
                    'url': info.get('url', ''),
                    'thumbnail': info.get('video', {}).get('cover', {}).get('url_list', [''])[0]
                })

        # Send to AI for scoring
        openrouter_key = os.environ.get('OPENROUTER_API_KEY')
        results = []
        for v in filtered[:3]:
            ai_data = json.dumps({
                "model": "google/gemini-2.5-flash",
                "messages": [{
                    "role": "user",
                    "content": f"Rate this TikTok 1-10 for Hoxton Wealth (expat financial planning company). Reply ONLY as JSON: {{\"score\": number, \"reason\": \"one sentence\"}}. Caption: {v['desc'][:300]}"
                }]
            }).encode()

            ai_req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=ai_data,
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                }
            )
            try:
                with urllib.request.urlopen(ai_req) as ai_r:
                    ai_result = json.loads(ai_r.read())
                    text = ai_result["choices"][0]["message"]["content"]
                    text = text.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(text)
                    v['score'] = parsed['score']
                    v['reason'] = parsed['reason']
            except:
                v['score'] = 5
                v['reason'] = 'Could not analyze'
            results.append(v)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(results).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()