import json
import feedparser
from datetime import datetime

UPDATED = datetime.now().strftime("Aggiornato il %d/%m/%Y")

FEEDS = {
    "penale": "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
    "famiglia": "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
    "patrocinio": "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
    "giurisprudenza": "https://feeds.feedburner.com/studiocataldi/PrimaPagina"
}

def clean(text):
    return " ".join((text or "").replace("\n", " ").split())

result = {}

for category, url in FEEDS.items():
    feed = feedparser.parse(url)
    items = []

    for entry in feed.entries[:6]:
        title = clean(getattr(entry, "title", ""))
        link = clean(getattr(entry, "link", ""))
        desc = clean(getattr(entry, "summary", ""))

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "description": desc[:220],
                "date": UPDATED
            })

    result[category] = items

with open("data/news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("news.json aggiornato")
