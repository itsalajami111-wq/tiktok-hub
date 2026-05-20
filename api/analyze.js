export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).end();

  try {
    const { keyword = 'financial planning' } = req.body;
    const scrapeKey = process.env.SCRAPE_API_KEY;
    const openrouterKey = process.env.OPENROUTER_API_KEY;

    // Step 1 - Search TikTok
    const response = await fetch(
      `https://api.scrapecreators.com/v1/tiktok/search/keyword?query=${encodeURIComponent(keyword)}`,
      { headers: { 'x-api-key': scrapeKey } }
    );
    const data = await response.json();
    const videos = data.search_item_list || [];

    // Step 2 - Filter first (before AI)
    const filtered = videos
      .map(item => {
        const info = item.aweme_info || {};
        const stats = info.statistics || {};
        return {
          author: info.author?.nickname || '',
          username: info.author?.unique_id || '',
          desc: info.desc || '',
          views: stats.play_count || 0,
          likes: stats.digg_count || 0,
          comments: stats.comment_count || 0,
          shares: stats.share_count || 0,
          saves: stats.collect_count || 0,
          url: info.url || '',
          thumbnail: info.video?.cover?.url_list?.[0] || '',
          duration: info.video?.duration || 0,
        };
      })
      .filter(v => v.views >= 100000 && v.likes >= 2000);

    // Step 3 - Send ONLY filtered videos to AI
    const results = [];
    for (const v of filtered.slice(0, 5)) {
      const prompt = `
You are a content strategist for Hoxton Wealth, a financial planning company that specifically serves expats (people living outside their home country). 

Analyze this TikTok video and give a detailed assessment:

Creator: @${v.author}
Caption: ${v.desc}
Views: ${v.views.toLocaleString()}
Likes: ${v.likes.toLocaleString()}
Comments: ${v.comments.toLocaleString()}
Shares: ${v.shares.toLocaleString()}
Saves: ${v.saves.toLocaleString()}
Duration: ${v.duration} seconds

Please answer:
1. RELEVANCE SCORE (1-10): How relevant is this for Hoxton Wealth's expat audience?
2. TOPIC: What financial topic does this cover? (e.g. investing, budgeting, tax, retirement)
3. AUDIENCE FIT: Does this match expats with complex financial needs? Yes/No and why
4. TONE: Is the tone professional enough for Hoxton Wealth? Yes/No
5. CONTENT IDEA: How could Hoxton Wealth create a similar video for expats?
6. ONE LINE SUMMARY: One sentence summary of why this is or isn't useful

Reply ONLY as JSON:
{
  "score": number,
  "topic": "string",
  "audience_fit": "string",
  "tone": "string", 
  "content_idea": "string",
  "summary": "string"
}`;

      try {
        const aiResponse = await fetch('https://openrouter.ai/api/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${openrouterKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: 'google/gemini-2.5-flash',
            messages: [{ role: 'user', content: prompt }]
          })
        });

        const aiData = await aiResponse.json();
        const text = aiData.choices?.[0]?.message?.content || '';
        const clean = text.replace(/```json|```/g, '').trim();
        const parsed = JSON.parse(clean);

        results.push({ ...v, ...parsed });
      } catch (e) {
        results.push({
          ...v,
          score: 5,
          topic: 'Finance',
          audience_fit: 'Unknown',
          tone: 'Unknown',
          content_idea: 'Could not analyze',
          summary: 'AI analysis unavailable'
        });
      }
    }

    // Sort by score
    results.sort((a, b) => b.score - a.score);
    res.status(200).json(results);

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
