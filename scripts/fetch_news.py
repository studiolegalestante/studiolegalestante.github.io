import json
import feedparser
from datetime import datetime
import sys

FEEDS = {
    "penale": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=penale",  # aggiornato spesso
        "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
        "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
        "https://feeds.feedburner.com/studiocataldi/PrimaPagina",
    ],
    "famiglia": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=famiglia",
        "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
        "https://feeds.feedburner.com/studiocataldi/PrimaPagina",
    ],
    "patrocinio": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php",
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=penale",
        "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche",
        "https://feeds.feedburner.com/StudioCataldi-DirittoPenale",
        "https://feeds.feedburner.com/studiocataldi/PrimaPagina",
    ],
    "giurisprudenza": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=cassazione",
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=giurisprudenza-di-merito",
        "https://feeds.feedburner.com/studiocataldi/PrimaPagina",
        "https://feeds.feedburner.com/StudioCataldi-NewsPiuLette",
    ],
}

PATROCINIO_KEYWORDS = [
    "patrocinio",
    "gratuito patrocinio",
    "spese dello stato",
    "spese di giustizia",
    "non abbiente",
    "ammissione al beneficio",
    "difensore d'ufficio",
    "difesa d'ufficio",
    "assistenza legale gratuita",
    "indigente",
    "ammissione al patrocinio",
    "DPR 115",
    "contributo unificato",
    "accesso alla giustizia",
    "reddito ammissione",
    "soglia reddito",
]

PATROCINIO_FALLBACK = [
    {
        "title": "Patrocinio a spese dello Stato: requisiti e come richiederlo",
        "link": "https://www.studiocataldi.it/articoli/15377-gratuito-patrocinio-guida-e-fac-simile-dell-istanza.asp",
        "description": "Il gratuito patrocinio consente alle persone non abbienti di essere assistite da un avvocato con spese a carico dello Stato. Guida ai requisiti reddituali e alla procedura.",
        "date": "01/01/2025",
    },
    {
        "title": "Gratuito patrocinio: la soglia di reddito aggiornata",
        "link": "https://www.studiocataldi.it/articoli/36107-limite-reddito-gratuito-patrocinio.asp",
        "description": "La soglia di reddito per l'ammissione al patrocinio a spese dello Stato è aggiornata periodicamente. Chi non supera il limite ha diritto all'assistenza legale gratuita.",
        "date": "01/01/2025",
    },
    {
        "title": "Patrocinio a spese dello Stato anche per lo straniero",
        "link": "https://www.studiocataldi.it/articoli/28738-patrocinio-a-spese-dello-stato-anche-per-lo-straniero.asp",
        "description": "Il gratuito patrocinio spetta anche ai cittadini stranieri regolarmente soggiornanti in Italia, purché in possesso dei requisiti reddituali previsti dal DPR 115/2002.",
        "date": "01/01/2025",
    },
    {
        "title": "Gratuito patrocinio: l'istanza si presenta al Consiglio dell'Ordine",
        "link": "https://www.studiocataldi.it/articoli/14619-gratuito-patrocinio.asp",
        "description": "Per essere ammessi al patrocinio a spese dello Stato occorre presentare apposita istanza al Consiglio dell'Ordine degli Avvocati competente, allegando la documentazione reddituale.",
        "date": "01/01/2025",
    },
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


def load_existing(category):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(category, [])
    except Exception:
        return []


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

            # Filtro solo per patrocinio
            if category == "patrocinio" and not matches_keywords(title, desc, PATROCINIO_KEYWORDS):
                continue

            seen_links.add(link)
            items.append({
                "title": title,
                "link": link,
                "description": desc[:220],
                "date": date,
            })

    # Integra con articoli salvati in precedenza se mancano pezzi
    if len(items) < MAX_ITEMS:
        print(f"  ℹ️  Solo {len(items)} articoli nuovi, integro con archivio precedente...")
        for old in load_existing(category):
            if len(items) >= MAX_ITEMS:
                break
            if old["link"] not in seen_links:
                seen_links.add(old["link"])
                items.append(old)

    # Per patrocinio usa i fallback fissi se ancora non basta
    if category == "patrocinio" and len(items) < MAX_ITEMS:
        print(f"  ℹ️  Integro con articoli di fallback fissi...")
        for fb in PATROCINIO_FALLBACK:
            if len(items) >= MAX_ITEMS:
                break
            if fb["link"] not in seen_links:
                seen_links.add(fb["link"])
                items.append(fb)

    result[category] = items
    print(f"  → {len(items)} articoli salvati")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

totale = sum(len(v) for v in result.values())
print(f"\n✅ Salvato {OUTPUT_FILE} con {totale} articoli totali")
