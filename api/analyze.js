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

    const filtered = videos
      .map(item => {
        const info = item.aweme_info || {};
        const stats = info.statistics || {};
        return {
          author: info.author?.nickname || '',
          desc: info.desc || '',
          views: stats.play_count || 0,
          likes: stats.digg_count || 0,
          url: info.url || '',
          thumbnail: info.video?.cover?.url_list?.[0] || '',
          score: 7,
          reason: 'High engagement financial content'
        };
      })
      .filter(v => v.views >= 100000 && v.likes >= 2000);

    res.status(200).json(filtered);

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
