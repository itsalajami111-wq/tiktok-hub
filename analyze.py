from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length))
            keyword = body.get('keyword', 'financial planning')

            scrape_key = os.environ.get('SCRAPE_API_KEY', '')
            
            url = f"https://api.scrapecreators.com/v1/tiktok/search/keyword?query={urllib.parse.quote(keyword)}"
            req = urllib.request.Request(url, headers={"x-api-key": scrape_key})
            
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read())

            videos = data.get('search_item_list', [])
            results = []
            
            for item in videos[:5]:
                info = item.get('aweme_info', {})
                stats = info.get('statistics', {})
                views = stats.get('play_count', 0)
                likes = stats.get('digg_count', 0)
                
                if views >= 100000 and likes >= 2000:
                    results.append({
                        'author': info.get('author', {}).get('nickname', ''),
                        'desc': info.get('desc', ''),
                        'views': views,
                        'likes': likes,
                        'url': info.get('url', ''),
                        'thumbnail': info.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                        'score': 7,
                        'reason': 'High engagement — relevant financial content'
                    })

            response = json.dumps(results).encode()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
