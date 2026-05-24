import json
import feedparser
from datetime import datetime
import sys

FEEDS = {
    "penale": [
        "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=penale",
    ],
    "famiglia": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=famiglia",
        "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
    ],
    "patrocinio": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php",
        "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
        "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
    ],
    "giurisprudenza": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=cassazione",
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=giurisprudenza-di-merito",
        "https://feeds.feedburner.com/studiocataldi/PrimaPagina",
    ],
}

FAMIGLIA_KEYWORDS = [
    "famiglia", "divorzio", "separazione", "affido", "mantenimento",
    "matrimonio", "coniuge", "minore", "genitore", "adozione",
    "assegno", "ex moglie", "ex marito", "figlio", "custodia",
    "filiazione", "tutela", "convivenza", "unione civile",
]

PATROCINIO_KEYWORDS = [
    "patrocinio", "gratuito patrocinio", "spese dello stato",
    "non abbiente", "ammissione al beneficio", "difesa d'ufficio",
    "reddito ammissione", "assistenza legale gratuita", "indigente",
    "ammissione al patrocinio", "DPR 115",
]

OUTPUT_FILE = "data/news.json"
MAX_ITEMS = 6


def clean(text):
    return " ".join((text or "").replace("\n", " ").split())


def parse_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6])
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    return datetime.now().strftime("%d/%m/%Y")


def fetch_feed(url):
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"  ⚠️  Feed vuoto o non valido: {url}", file=sys.stderr)
            return []
        print(f"  ✅ {len(feed.entries)} articoli da {url}")
        return feed.entries
    except Exception as e:
        print(f"  ❌ Errore su {url}: {e}", file=sys.stderr)
        return []


def matches_keywords(title, desc, keywords):
    text = (title + " " + desc).lower()
    return any(kw.lower() in text for kw in keywords)


result = {}

for category, urls in FEEDS.items():
    print(f"\n📂 Categoria: {category}")
    items = []
    seen_links = set()

    for url in urls:
        if len(items) >= MAX_ITEMS:
            break
        for entry in fetch_feed(url):
            if len(items) >= MAX_ITEMS:
                break

            title = clean(getattr(entry, "title", ""))
            link  = clean(getattr(entry, "link", ""))
            desc  = clean(getattr(entry, "summary", ""))
            date  = parse_date(entry)

            if not title or not link or link in seen_links:
                continue

            if category == "famiglia" and not matches_keywords(title, desc, FAMIGLIA_KEYWORDS):
                continue
            if category == "patrocinio" and not matches_keywords(title, desc, PATROCINIO_KEYWORDS):
                continue

            seen_links.add(link)
            items.append({
                "title": title,
                "link": link,
                "description": desc[:220],
                "date": date,
            })

    # Placeholder se patrocinio resta vuoto
    if category == "patrocinio" and not items:
        print("  ⚠️  Nessun articolo trovato, uso placeholder")
        items.append({
            "title": "Patrocinio a spese dello Stato: guida completa",
            "link": "https://www.studiocataldi.it/articoli/15377-gratuito-patrocinio-guida-e-fac-simile-dell-istanza.asp",
            "description": "Il gratuito patrocinio consente alle persone non abbienti di essere assistite da un avvocato con spese a carico dello Stato. Guida ai requisiti e alla procedura di ammissione.",
            "date": datetime.now().strftime("%d/%m/%Y"),
        })

    result[category] = items
    print(f"  → {len(items)} articoli salvati")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

totale = sum(len(v) for v in result.values())
print(f"\n✅ Salvato {OUTPUT_FILE} con {totale} articoli totali")
