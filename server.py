from flask import Flask, request, jsonify
import os
import urllib.request
import urllib.parse
import json

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    data = request.get_json()
    keyword = data.get('keyword', 'financial planning')
    scrape_key = os.environ.get('SCRAPE_API_KEY', '')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY', '')

    # Step 1 - Search TikTok
    url = f"https://api.scrapecreators.com/v1/tiktok/search/keyword?query={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(url, headers={"x-api-key": scrape_key})
    with urllib.request.urlopen(req, timeout=30) as r:
        tiktok_data = json.loads(r.read())

    videos = tiktok_data.get('search_item_list', [])

    # Step 2 - Filter first
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
                'comments': stats.get('comment_count', 0),
                'shares': stats.get('share_count', 0),
                'saves': stats.get('collect_count', 0),
                'url': info.get('url', ''),
                'thumbnail': info.get('video', {}).get('cover', {}).get('url_list', [''])[0],
            })

    # Step 3 - Send filtered videos to AI
    results = []
    for v in filtered[:5]:
        prompt = f"""You are a content strategist for Hoxton Wealth, a financial planning company for expats.

Analyze this TikTok video:
Creator: @{v['author']}
Caption: {v['desc'][:300]}
Views: {v['views']:,}
Likes: {v['likes']:,}
Comments: {v['comments']:,}
Shares: {v['shares']:,}

Answer:
1. RELEVANCE SCORE (1-10) for Hoxton Wealth expat audience
2. TOPIC: What financial topic does this cover?
3. AUDIENCE FIT: Does this match expats with complex financial needs?
4. TONE: Is the tone professional enough for Hoxton Wealth?
5. CONTENT IDEA: How could Hoxton Wealth create a similar video for expats?
6. SUMMARY: One sentence summary

Reply ONLY as JSON:
{{"score": number, "topic": "string", "audience_fit": "string", "tone": "string", "content_idea": "string", "summary": "string"}}"""

        try:
            ai_data = json.dumps({
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt}]
            }).encode()

            ai_req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=ai_data,
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(ai_req, timeout=60) as ai_r:
                ai_result = json.loads(ai_r.read())
                text = ai_result["choices"][0]["message"]["content"]
                text = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text)
                v.update(parsed)
        except Exception as e:
            v.update({
                'score': 5,
                'topic': 'Finance',
                'audience_fit': 'Unknown',
                'tone': 'Unknown',
                'content_idea': 'Could not analyze',
                'summary': str(e)
            })
        results.append(v)

    results.sort(key=lambda x: x['score'], reverse=True)
    response = jsonify(results)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
