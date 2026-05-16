#!/usr/bin/env python3
"""Generate a realistic sample news.json so the page renders before the
first GitHub Actions run. Replaces itself with real data once the workflow
runs. Mirrors the schema produced by aggregate.py exactly."""
import json, time, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

def make_id(t, l): return hashlib.sha1(f"{t}|{l}".encode()).hexdigest()[:12]

now = datetime.now(tz=timezone.utc)

# (title, summary, source, domain, region, category, hours_ago, priority,
#  hindi_title or None, related_sources)
seeds = [
    ("Israel and Hamas reach ceasefire deal, hostages to be released in phased plan",
     "Negotiators from Egypt and Qatar announced the agreement late Thursday after months of stalled talks. Initial release of 33 hostages is expected within the first phase, alongside a partial Israeli withdrawal from key Gaza corridors.",
     "Reuters", "reuters.com", "intl", "war", 1, 92, None,
     [{"name": "BBC World", "domain": "bbc.com", "link": "https://www.bbc.com/news/world-12345"},
      {"name": "Al Jazeera", "domain": "aljazeera.com", "link": "https://www.aljazeera.com/news/example"}]),

    ("Sensex closes above 86,000 for first time as RBI signals dovish stance",
     "Benchmark indices ended at record highs after the central bank held the repo rate at 6.25% and hinted at possible easing in Q2. Banking and IT stocks led the rally with the Nifty gaining 1.4%.",
     "Moneycontrol", "moneycontrol.com", "india", "markets", 2, 86, None,
     [{"name": "Economic Times", "domain": "economictimes.indiatimes.com", "link": "https://economictimes.indiatimes.com/example"},
      {"name": "Livemint", "domain": "livemint.com", "link": "https://livemint.com/example"}]),

    ("OpenAI unveils GPT-5.5 with breakthrough multi-step reasoning",
     "The new model shows substantial improvements on competition math and scientific reasoning benchmarks. OpenAI says GPT-5.5 reduces hallucinations by 40% and ships to ChatGPT Plus and Enterprise users this week.",
     "The Verge", "theverge.com", "intl", "ai", 3, 84, None,
     [{"name": "TechCrunch", "domain": "techcrunch.com", "link": "https://techcrunch.com/example"},
      {"name": "Ars Technica", "domain": "arstechnica.com", "link": "https://arstechnica.com/example"},
      {"name": "MIT Tech Review", "domain": "technologyreview.com", "link": "https://technologyreview.com/example"}]),

    ("PM Modi inaugurates ₹1.2 lakh crore Mumbai-Ahmedabad bullet train corridor",
     "The 508-km high-speed rail link, India's first, will cut travel time between the two cities to about two hours. Commercial operations are slated to begin in phases starting next year.",
     "NDTV", "ndtv.com", "india", "politics", 4, 78,
     "पीएम मोदी ने मुंबई-अहमदाबाद बुलेट ट्रेन का उद्घाटन किया",
     [{"name": "Times of India", "domain": "timesofindia.indiatimes.com", "link": "https://timesofindia.indiatimes.com/example"},
      {"name": "Hindustan Times", "domain": "hindustantimes.com", "link": "https://hindustantimes.com/example"}]),

    ("Federal Reserve cuts rates by 25 bps, signals two more cuts in 2026",
     "The Federal Open Market Committee lowered the benchmark rate to a 3.75–4.00% range. Chair Powell cited cooling inflation but warned of persistent labour-market softness. Markets rallied on the dovish tilt.",
     "Bloomberg", "bloomberg.com", "intl", "economy", 5, 82, None,
     [{"name": "CNBC", "domain": "cnbc.com", "link": "https://cnbc.com/example"},
      {"name": "Reuters", "domain": "reuters.com", "link": "https://reuters.com/example"}]),

    ("Pakistan floods displace over 2 million as monsoon damages intensify",
     "Sindh and southern Punjab are the worst-hit. The UN has launched an emergency appeal for $400 million. Pakistani authorities say at least 380 people have died in the past week.",
     "BBC World", "bbc.com", "intl", "environment", 6, 80, None,
     [{"name": "Al Jazeera", "domain": "aljazeera.com", "link": "https://aljazeera.com/example"}]),

    ("ISRO successfully launches Chandrayaan-4 lunar sample return mission",
     "The spacecraft lifted off from Sriharikota at 5:42 IST aboard the LVM3 rocket. The mission will return surface samples from the lunar south pole region — a first for any space agency since Chang'e 5.",
     "The Hindu", "thehindu.com", "india", "science", 7, 76,
     None,
     [{"name": "Indian Express", "domain": "indianexpress.com", "link": "https://indianexpress.com/example"},
      {"name": "NDTV", "domain": "ndtv.com", "link": "https://ndtv.com/example"}]),

    ("Apple unveils foldable iPhone with 7.8-inch interior display",
     "At its annual hardware event, Apple revealed the long-rumoured foldable iPhone, branded 'iPhone Fold'. Starting at $2,299 in the US, ₹2,29,900 in India, with shipments beginning next month.",
     "TechCrunch", "techcrunch.com", "intl", "technology", 8, 70, None,
     [{"name": "The Verge", "domain": "theverge.com", "link": "https://theverge.com/example"},
      {"name": "BBC Tech", "domain": "bbc.com", "link": "https://bbc.com/example"}]),

    ("India beat Australia by 6 wickets in T20I series decider",
     "Chasing 198 at the MCG, India coasted home with eight balls to spare. Suryakumar Yadav scored an unbeaten 84 off 47 balls and was named player of the match and series.",
     "NDTV Sports", "sports.ndtv.com", "india", "sports", 9, 60, None, []),

    ("UN climate summit in Brasília ends with new fossil-fuel transition pact",
     "Delegates from 195 countries agreed to a non-binding roadmap accelerating the phase-down of unabated fossil fuels by 2035. Climate activists called the language watered-down but welcomed the financing pledges.",
     "France 24", "france24.com", "intl", "environment", 10, 78, None,
     [{"name": "Deutsche Welle", "domain": "dw.com", "link": "https://dw.com/example"},
      {"name": "BBC World", "domain": "bbc.com", "link": "https://bbc.com/example"}]),

    ("Bollywood: Shah Rukh Khan's 'King' release date pushed to Diwali 2026",
     "Producers confirmed the schedule change citing extended post-production. The film, directed by Siddharth Anand, also stars Suhana Khan in her first big-screen lead role.",
     "Bollywood Hungama", "bollywoodhungama.com", "india", "bollywood", 11, 40, None, []),

    ("Hollywood: 'Dune: Messiah' breaks $300m global opening weekend",
     "Denis Villeneuve's third Dune film opened to record numbers, with strong showings in IMAX and Dolby. Critics are praising the film as 'visually overwhelming' while some flag pacing issues.",
     "Variety", "variety.com", "intl", "hollywood", 12, 42, None, []),

    ("New AI-designed antibiotic shows promise against drug-resistant TB",
     "Researchers at MIT and Hyderabad's CSIR-CCMB published results in Nature showing the compound is effective against multi-drug-resistant tuberculosis strains in animal trials. Human trials are expected next year.",
     "MIT Tech Review", "technologyreview.com", "intl", "health", 14, 72, None,
     [{"name": "The Hindu", "domain": "thehindu.com", "link": "https://thehindu.com/example"}]),

    ("CBSE announces revamped board exam pattern from 2027",
     "The new pattern will include two exam attempts per academic year and a competency-based question structure. Education Minister said the reforms aim to reduce exam stress and align with NEP 2020.",
     "The Hindu Education", "thehindu.com", "india", "education", 15, 58, None,
     [{"name": "Indian Express", "domain": "indianexpress.com", "link": "https://indianexpress.com/example"}]),

    ("German fashion house Hugo Boss appoints new creative director",
     "The Stuttgart-based brand named former Balenciaga designer Léa Martin as creative head. The appointment is seen as part of Hugo Boss's push toward a more avant-garde aesthetic.",
     "Deutsche Welle", "dw.com", "intl", "fashion", 18, 35, None, []),

    ("Octopus appears to plan ahead, new study suggests",
     "Researchers at the University of Naples observed octopuses gathering tools for future use — behaviour previously seen only in primates and corvids. The findings, published in Current Biology, reopen debates about cephalopod cognition.",
     "BBC Science", "bbc.com", "intl", "quirky", 20, 30, None, []),

    ("Adani Group announces $50 billion green energy push by 2030",
     "The conglomerate said it will scale solar and green hydrogen capacity dramatically, with most of the investment going into Gujarat and Rajasthan plants. Shares of Adani Green rose 4% on the news.",
     "Business Standard", "business-standard.com", "india", "business", 22, 68, None,
     [{"name": "Moneycontrol", "domain": "moneycontrol.com", "link": "https://moneycontrol.com/example"}]),

    ("Wimbledon 2026: Alcaraz wins fourth consecutive title in five-set thriller",
     "Carlos Alcaraz defeated Jannik Sinner 6-4, 5-7, 6-2, 4-6, 7-5 in a four-hour final. The win cements his place among the modern greats and earns him a record-tying fourth straight grass-court Slam.",
     "BBC Sport", "bbc.com", "intl", "sports", 26, 64, None,
     [{"name": "Sky News", "domain": "skynews.com", "link": "https://skynews.com/example"}]),

    ("Cybersecurity: Major data breach hits Indian telecom, 80M users affected",
     "An anonymous threat actor claims to have leaked subscriber records including names, addresses and Aadhaar-linked KYC fragments. The telecom is investigating but has not confirmed the scope.",
     "Indian Express", "indianexpress.com", "india", "technology", 30, 74, None,
     [{"name": "NDTV", "domain": "ndtv.com", "link": "https://ndtv.com/example"}]),

    ("Bitcoin breaks $130,000 amid spot-ETF inflows surge",
     "The cryptocurrency hit a fresh all-time high as institutional inflows topped $2 billion in a single week. Analysts cite supply-tightening from the recent halving as a continuing driver.",
     "CNBC", "cnbc.com", "intl", "markets", 36, 60, None, []),

    ("Tokyo unveils world's first carbon-negative office tower",
     "The 52-storey structure uses engineered timber and on-site algae bioreactors. The Japanese government says the design could become a template for new commercial construction nationwide.",
     "NHK World", "nhk.or.jp", "intl", "environment", 50, 48, None, []),

    ("Goa man wins ₹15 crore lottery, says he'll use it to open a free school",
     "Local resident Manuel D'Souza, 54, said the win 'won't change my house' but will fund a free school for fishermen's children near Panjim. The story has gone viral on Indian social media.",
     "NDTV", "ndtv.com", "india", "quirky", 72, 28, None, []),
]

articles = []
for t, s, src, dom, region, cat, hrs, pri, hi, related in seeds:
    pub = now - timedelta(hours=hrs)
    articles.append({
        "id": make_id(t, f"https://{dom}/"),
        "title": t,
        "title_hindi": hi,
        "summary": s,
        "link": f"https://{dom}/",
        "source": src,
        "source_domain": dom,
        "region": region,
        "category": cat,
        "published_iso": pub.isoformat(),
        "published_ts": int(pub.timestamp()),
        "has_hindi": bool(hi),
        "priority": pri,
        "keywords": [],
        "anchors": [],
        "related_sources": related,
    })

# Sort by priority desc, then recency desc (matches aggregate.py)
articles.sort(key=lambda a: (a["priority"], a["published_ts"]), reverse=True)

from collections import Counter
payload = {
    "generated_at": now.isoformat(),
    "generated_ts": int(now.timestamp()),
    "total": len(articles),
    "category_counts": dict(Counter(a["category"] for a in articles)),
    "region_counts": dict(Counter(a["region"] for a in articles)),
    "category_order": ["war","politics","government","economy","markets","business","ai","technology","science","health","environment","education","sports","bollywood","hollywood","entertainment","fashion","quirky","world","india"],
    "articles": articles,
    "is_sample": True,
}

out = Path(__file__).resolve().parent.parent / "data" / "news.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {out} ({len(articles)} sample articles)")
