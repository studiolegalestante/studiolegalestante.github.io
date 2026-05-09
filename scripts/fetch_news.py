import json
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = {
    "penale": [
        "https://news.avvocatoandreani.it/news-giuridiche/feed-rss.php"
    ],
    "famiglia": [
        "https://news.avvocatoandreani.it/news-giuridiche/feed-rss.php"
    ],
    "patrocinio": [
        "https://www.studiocataldi.it/feed_rss.asp"
    ],
    "giurisprudenza": [
        "https://news.avvocatoandreani.it/news-giuridiche/feed-rss.php",
        "https://www.studiocataldi.it/feed_rss.asp"
    ]
}

KEYWORDS = {
    "penale": ["penale", "reato", "cassazione penale", "misura cautelare", "imputato", "processo penale"],
    "famiglia": ["famiglia", "separazione", "divorzio", "affidamento", "mantenimento", "minori"],
    "patrocinio": ["patrocinio", "spese dello stato", "gratuito patrocinio", "non abbienti"],
    "giurisprudenza": ["cassazione", "sentenza", "tribunale", "corte", "giurisprudenza"]
}

def fetch(feed):
    req = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def clean(text):
    return " ".join((text or "").replace("\n", " ").split())

def parse_feed(feed_url):
    items = []
    try:
        root = ET.fromstring(fetch(feed_url))
        for item in root.findall(".//item"):
            title = clean(item.findtext("title"))
            link = clean(item.findtext("link"))
            desc = clean(item.findtext("description"))
            pub = clean(item.findtext("pubDate"))
            try:
                date = parsedate_to_datetime(pub).strftime("%d/%m/%Y") if pub else ""
            except Exception:
                date = ""

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "description": desc[:220],
                    "date": date,
                    "source": feed_url
                })
    except Exception as e:
        print(f"Errore feed {feed_url}: {e}")
    return items

def relevant(item, category):
    text = (item["title"] + " " + item["description"]).lower()
    return any(k in text for k in KEYWORDS[category])

result = {}

for category, feeds in FEEDS.items():
    collected = []
    seen = set()

    for feed in feeds:
        for item in parse_feed(feed):
            if item["link"] in seen:
                continue
            if relevant(item, category):
                collected.append(item)
                seen.add(item["link"])

    result[category] = collected[:6]

with open("data/news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
