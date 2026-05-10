import json
import feedparser
from datetime import datetime

FEED = "https://news.avvocatoandreani.it/news-giuridiche/feed-rss.php"
UPDATED = datetime.now().strftime("Aggiornato il %d/%m/%Y")

CATEGORIES = {
    "penale": ["penale", "reato", "reati", "imputato", "condanna", "carcere", "misura cautelare"],
    "famiglia": ["famiglia", "separazione", "divorzio", "affidamento", "mantenimento", "minori", "figli"],
    "patrocinio": ["patrocinio", "spese dello stato", "gratuito patrocinio", "non abbienti"],
    "giurisprudenza": ["cassazione", "sentenza", "tribunale", "corte", "giurisprudenza"]
}

def clean(text):
    return " ".join((text or "").replace("\n", " ").split())

feed = feedparser.parse(FEED)

all_items = []
for entry in feed.entries:
    title = clean(getattr(entry, "title", ""))
    link = clean(getattr(entry, "link", ""))
    desc = clean(getattr(entry, "summary", ""))

    if title and link:
        all_items.append({
            "title": title,
            "link": link,
            "description": desc[:220],
            "date": UPDATED
        })

result = {}

for category, keywords in CATEGORIES.items():
    selected = []
    for item in all_items:
        text = (item["title"] + " " + item["description"]).lower()
        if any(k in text for k in keywords):
            selected.append(item)

    result[category] = selected[:6] if selected else all_items[:6]

with open("data/news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("news.json aggiornato correttamente")
