import json
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = {
    "penale": "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
    "famiglia": "https://www.ilsole24ore.com/rss/norme-e-tributi--diritto.xml",
    "patrocinio": "https://www.ilsole24ore.com/rss/norme-e-tributi--diritto.xml",
    "giurisprudenza": "https://www.ilsole24ore.com/rss/norme-e-tributi--diritto.xml"
}

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse_feed(url):
    data = fetch(url)
    root = ET.fromstring(data)

    news = []

    for item in root.findall(".//item")[:6]:

        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        desc = item.findtext("description", "").strip()
        pub = item.findtext("pubDate", "").strip()

        try:
            pub = parsedate_to_datetime(pub).strftime("%d/%m/%Y")
        except Exception:
            pass

        news.append({
            "title": title,
            "link": link,
            "description": desc[:180],
            "date": pub
        })

    return news

result = {}

for category, feed in FEEDS.items():
    try:
        result[category] = parse_feed(feed)
    except Exception as e:
        result[category] = [{
            "title": f"Feed temporaneamente non disponibile ({category})",
            "link": "#",
            "description": str(e),
            "date": ""
        }]

with open("data/news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("news.json aggiornato")
