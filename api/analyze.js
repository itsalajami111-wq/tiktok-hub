export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).end();

  try {
    const { keyword = 'financial planning' } = req.body;
    const scrapeKey = process.env.SCRAPE_API_KEY;

    const response = await fetch(
      `https://api.scrapecreators.com/v1/tiktok/search/keyword?query=${encodeURIComponent(keyword)}`,
      { headers: { 'x-api-key': scrapeKey } }
    );

    const data = await response.json();
    const videos = data.search_item_list || [];

    const results = videos
      .map(item => {
        const info = item.aweme_info || {};
        const stats = info.statistics || {};
        const desc = info.desc || '';
        const views = stats.play_count || 0;
        const likes = stats.digg_count || 0;
        const keywords = ['expat','invest','wealth','retire','abroad','offshore','tax','pension','savings','financial'];
        const matches = keywords.filter(k => desc.toLowerCase().includes(k)).length;
        const score = Math.min(10, 5 + matches + (views > 500000 ? 1 : 0) + (likes > 50000 ? 1 : 0));
        return {
          author: info.author?.nickname || '',
          desc,
          views,
          likes,
          comments: stats.comment_count || 0,
          shares: stats.share_count || 0,
          saves: stats.collect_count || 0,
          url: info.url || '',
          thumbnail: info.video?.cover?.url_list?.[0] || '',
          score,
          topic: matches > 0 ? 'Expat Finance' : 'General Finance',
          audience_fit: matches > 1 ? 'Good fit for expat audience' : 'Needs expat angle',
          tone: likes > 10000 ? 'High engagement' : 'Moderate engagement',
          content_idea: 'Adapt with expat-specific financial advice for Hoxton Wealth',
          summary: `${views.toLocaleString()} views — ${matches} expat keywords found`
        };
      })
      .filter(v => v.views >= 100000 && v.likes >= 2000)
      .sort((a, b) => b.score - a.score);

    res.status(200).json(results);

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
