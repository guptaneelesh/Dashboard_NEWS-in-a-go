# Daily Brief — Global & India News Dashboard

A static, GitHub-Pages-hostable news dashboard that aggregates RSS feeds from major international and Indian outlets, deduplicates near-identical stories across sources, ranks by priority, and updates daily via GitHub Actions.

## What it does

- Pulls RSS from ~45 reputable feeds: BBC, Reuters, Al Jazeera, Sky, France 24, DW, NHK, NPR, AP, AFP (via Google News), CNBC, Bloomberg, TechCrunch, The Verge, Ars Technica, MIT Tech Review, NASA, Variety, NDTV (English + Hindi), The Hindu, Indian Express, India Today, Times of India, Scroll, Hindustan Times, Moneycontrol, ET, Business Standard, Livemint, Bollywood Hungama, and more.
- Classifies each item into one of 18 categories (war, politics, AI, markets, health, environment, sports, Bollywood, Hollywood, quirky, …).
- Clusters duplicate stories using **anchor token overlap** (proper nouns + abbreviations + numbers in the headline). The strongest article in each cluster becomes canonical; the rest are listed as "Also reported by".
- Scores priority based on global-impact keywords, India-impact keywords, crisis/economy signals, and number of corroborating sources.
- Preserves original Hindi headlines (Devanagari) when the source publishes in Hindi; renders them in a Devanagari font.
- Refreshes daily at **02:00 UTC** (~07:30 IST) via the `refresh-news.yml` workflow. You can also trigger it manually from the Actions tab.

## Filters in the UI

- **Region toggle**: All / International / India
- **Category dropdown**: all 18 categories, with counts
- **Time window**: last 1h / 2h / 6h / 24h / 7d
- **Free-text search** across title, summary, source, category

Clicking any headline opens the original publisher's article in a new tab.

## File layout

```
.
├── index.html                       # the dashboard (static; reads data/news.json)
├── data/
│   └── news.json                    # daily output; committed by the bot
├── scripts/
│   ├── aggregate.py                 # RSS fetcher, dedup, ranker
│   └── seed.py                      # generates sample data (already done)
└── .github/workflows/
    └── refresh-news.yml             # runs aggregate.py daily, commits news.json
```

## Setup (one-time)

1. Create a new public GitHub repo and push these files.
2. Go to **Settings → Pages**, set source to **Deploy from branch**, branch **main / (root)**. Wait ~30s; your dashboard goes live at `https://<your-user>.github.io/<repo>/`.
3. Go to **Settings → Actions → General**, scroll to **Workflow permissions**, choose **Read and write permissions**, save. (This lets the bot commit `news.json` back.)
4. Open the **Actions** tab → select **Refresh news feed** → **Run workflow**. After it succeeds, `data/news.json` will be updated and the dashboard will show real news.
5. From then on it runs daily on its own.

## Customizing

- **Add/remove feeds**: edit `FEEDS` in `scripts/aggregate.py`.
- **Tweak categories or keywords**: edit `CATEGORY_KEYWORDS` in the same file.
- **Change cadence**: edit the cron in `.github/workflows/refresh-news.yml` — e.g. `0 */6 * * *` for every 6 hours.
- **Visual theme**: all CSS variables are at the top of the `<style>` block in `index.html` (colors, radii, fonts).

## Caveats — please read

- **No scraping.** Only public RSS feeds are used. Each headline links to the publisher; copyrights remain with the publishers.
- **Feed availability changes.** A given outlet may rate-limit, change its RSS URL, or remove it altogether. The aggregator logs warnings for feeds that fail and continues with the rest.
- **Dedup is keyword-based, not semantic.** Two stories about the same event with very different phrasing may not merge. You said this was the desired tradeoff over AI-based dedup; if you change your mind, the dedup function in `aggregate.py` is the single hook to swap out.
- **Daily cadence.** This is a digest, not a real-time tracker. If you need sub-hour freshness, change the cron and accept the GitHub Actions usage.
- **Reuters and Bloomberg** are routed via Google News RSS because their direct feeds are restricted. Coverage is best-effort.
- **`is_sample: true`**: the seed `news.json` shipped with the repo is sample data so the page renders before your first workflow run. The first real run overwrites it.

## License of the dashboard code

The dashboard code is yours to modify and host. Article content, headlines, and summaries belong to the originating publishers and are surfaced under fair-use linking conventions.
