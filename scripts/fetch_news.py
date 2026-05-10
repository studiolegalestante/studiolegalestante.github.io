import json
import urllib.request
import xml.etree.ElementTree as ET
import re
import os
from email.utils import parsedate_to_datetime
from datetime import datetime

# Sorgenti aggiornate al 2026
FEEDS = {
    "penale": "https://avvocatoandreani.it",
    "famiglia": "https://avvocatoandreani.it",
    "giurisprudenza": "https://studiocataldi.it",
    "notizie_flash": "https://avvocatoandreani.it"
}

def clean_html(text):
    """Rimuove tag HTML e spazi eccessivi dalle descrizioni."""
    if not text: return ""
    clean = re.sub('<[^<]+?>', '', text)
    return clean.replace('&nbsp;', ' ').strip()

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

def parse_feed(url, category):
    try:
        data = fetch(url)
        root = ET.fromstring(data)
    except Exception as e:
        return [{"title": f"Errore feed {category}", "link": "#", "description": str(e), "date": ""}]

    news = []
    # Molti feed usano il namespace 'item' dentro 'channel'
    items = root.findall(".//item")
    
    for item in items[:6]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        desc = clean_html(item.findtext("description", ""))
        pub = item.findtext("pubDate", "").strip()

        try:
            # Formattazione data in italiano
            dt = parsedate_to_datetime(pub)
            date_str = dt.strftime("%d/%m/%Y")
        except:
            date_str = pub

        news.append({
            "title": title,
            "link": link,
            "description": desc[:200] + "..." if len(desc) > 200 else desc,
            "date": date_str
        })
    return news

# Assicura che la cartella di output esista
os.makedirs("data", exist_ok=True)

result = {}
for category, url in FEEDS.items():
    print(f"Aggiornamento {category}...")
    result[category] = parse_feed(url, category)

# Salvataggio finale
with open("data/news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ news.json aggiornato correttamente il {datetime.now().strftime('%d/%m/%Y %H:%M')}")
