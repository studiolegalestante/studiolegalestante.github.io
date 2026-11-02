import json
import os
import feedparser
import re
import requests
from datetime import datetime
import sys

FEEDS = {
    "penale": [
        "https://news.avvocatoandreani.it/feed/news_giuridiche.php?tags=penale",
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
        "image": "",
        "description": "Il gratuito patrocinio consente alle persone non abbienti di essere assistite da un avvocato con spese a carico dello Stato. Guida ai requisiti reddituali e alla procedura.",
        "date": "01/01/2025",
    },
    {
        "title": "Gratuito patrocinio: la soglia di reddito aggiornata",
        "link": "https://www.studiocataldi.it/articoli/36107-limite-reddito-gratuito-patrocinio.asp",
        "image": "",
        "description": "La soglia di reddito per l'ammissione al patrocinio a spese dello Stato è aggiornata periodicamente. Chi non supera il limite ha diritto all'assistenza legale gratuita.",
        "date": "01/01/2025",
    },
    {
        "title": "Patrocinio a spese dello Stato anche per lo straniero",
        "link": "https://www.studiocataldi.it/articoli/28738-patrocinio-a-spese-dello-stato-anche-per-lo-straniero.asp",
        "image": "",
        "description": "Il gratuito patrocinio spetta anche ai cittadini stranieri regolarmente soggiornanti in Italia, purché in possesso dei requisiti reddituali previsti dal DPR 115/2002.",
        "date": "01/01/2025",
    },
    {
        "title": "Gratuito patrocinio: l'istanza si presenta al Consiglio dell'Ordine",
        "link": "https://www.studiocataldi.it/articoli/14619-gratuito-patrocinio.asp",
        "image": "",
        "description": "Per essere ammessi al patrocinio a spese dello Stato occorre presentare apposita istanza al Consiglio dell'Ordine degli Avvocati competente, allegando la documentazione reddituale.",
        "date": "01/01/2025",
    },
]

OUTPUT_FILE = "data/news.json"
MAX_ITEMS = 6
MAX_CANDIDATI = 20  # articoli raccolti per categoria prima della selezione automatica

# Configurazione del servizio di sintesi: tutti i valori arrivano dalle variabili del repository.
AI = {k: os.environ.get("AI_" + k, "").strip() for k in
      ("BASE", "VERSION", "MODEL", "ORG", "RULE", "ACCOUNT", "WORKSPACE")}
AI_ATTIVA = all(AI.values())


def token_accesso():
    """Ottiene un accesso temporaneo tramite l'identità del workflow (nessuna chiave salvata)."""
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    bearer = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not bearer:
        raise RuntimeError("identità del workflow non disponibile")
    jwt = requests.get(url, params={"audience": AI["BASE"]},
                       headers={"Authorization": "Bearer " + bearer}, timeout=30).json()["value"]
    r = requests.post(AI["BASE"] + "/v1/oauth/token", json={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
        "federation_rule_id": AI["RULE"],
        "organization_id": AI["ORG"],
        "service_account_id": AI["ACCOUNT"],
        "workspace_id": AI["WORKSPACE"],
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


_TOKEN = None

DESCRIZIONE_CATEGORIA = {
    "penale": "diritto e procedura penale",
    "famiglia": "diritto di famiglia (separazione, divorzio, figli, mantenimento, successioni)",
    "patrocinio": "patrocinio a spese dello Stato e accesso alla giustizia per i non abbienti",
    "giurisprudenza": "sentenze rilevanti di Cassazione e dei giudici di merito, in materia civile, penale e di famiglia",
}


def clean(text):
    return " ".join((text or "").replace("\n", " ").split())


def extract_image(text):
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text)
    return match.group(1) if match else ""


def extract_text(text):
    clean_text = re.sub(r'<[^>]+>', '', text)
    return " ".join(clean_text.split())


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


def seleziona_con_ai(category, candidati):
    """Sceglie gli articoli più utili e scrive una sintesi originale.
    In caso di errore restituisce None e lo script usa il comportamento classico."""
    global _TOKEN
    if not AI_ATTIVA or not candidati:
        return None
    elenco = "\n".join(
        f"[{i}] {c['title']} — {c['description'][:400]}" for i, c in enumerate(candidati)
    )
    istruzioni = (
        "Sei il redattore della pagina notizie del sito di uno studio legale di Bari "
        f"che si occupa di {DESCRIZIONE_CATEGORIA[category]}. "
        f"Tra gli articoli elencati scegli i {MAX_ITEMS} più utili per un cittadino "
        "che cerca informazioni su questa materia, scartando quelli fuori tema, "
        "pubblicitari o duplicati. Per ciascuno scrivi una sintesi originale in italiano "
        "semplice, di massimo 200 caratteri, che dica cosa cambia o cosa ha deciso il giudice. "
        "Non copiare frasi dell'articolo, non inventare fatti che non risultano dal testo, "
        "non dare consigli legali. Rispondi solo con JSON nel formato "
        '[{"n": <numero articolo>, "sintesi": "<testo>"}], in ordine di importanza.'
    )
    try:
        if _TOKEN is None:
            _TOKEN = token_accesso()
        r = requests.post(
            AI["BASE"] + "/v1/messages",
            headers={
                "Authorization": "Bearer " + _TOKEN,
                AI["VERSION"].split("=")[0]: AI["VERSION"].split("=")[1],
                "content-type": "application/json",
            },
            json={
                "model": AI["MODEL"],
                "max_tokens": 8000,
                "system": istruzioni,
                "messages": [{"role": "user", "content": elenco}],
            },
            timeout=90,
        )
        r.raise_for_status()
        dati = r.json()
        testo = "".join(b.get("text", "") for b in dati.get("content", []))
        if not testo:
            tipi = [b.get("type") for b in dati.get("content", [])]
            raise ValueError(f"risposta vuota (stop: {dati.get('stop_reason')}, blocchi: {tipi})")
        trovato = re.search(r"\[\s*\{.*\}\s*\]", testo, re.S)
        if not trovato:
            raise ValueError("risposta senza elenco: " + testo[:120].replace("\n", " "))
        scelte = json.loads(trovato.group(0))
        out = []
        for s in scelte:
            i = int(s["n"])
            sintesi = clean(s.get("sintesi", ""))
            if len(sintesi) > 220:
                sintesi = sintesi[:220].rsplit(" ", 1)[0].rstrip(",;:") + "…"
            if 0 <= i < len(candidati) and sintesi and candidati[i] not in out:
                art = dict(candidati[i])
                art["description"] = sintesi
                art["ai"] = True
                out.append(art)
            if len(out) >= MAX_ITEMS:
                break
        print(f"  🤖 Selezione automatica: {len(out)} articoli")
        return out or None
    except Exception as e:
        print(f"  ⚠️  Selezione automatica non riuscita ({e}), uso il metodo classico", file=sys.stderr)
        return None


result = {}

for category, urls in FEEDS.items():
    print(f"\n📂 Categoria: {category}")
    items = []
    seen_links = set()
    limite = MAX_CANDIDATI if AI_ATTIVA else MAX_ITEMS

    for url in urls:
        if len(items) >= limite:
            break
        for entry in fetch_feed(url):
            if len(items) >= limite:
                break

            title = clean(getattr(entry, "title", ""))
            link  = clean(getattr(entry, "link", ""))
            raw   = clean(getattr(entry, "summary", ""))
            date  = parse_date(entry)

            if not title or not link or link in seen_links:
                continue

            if category == "patrocinio" and not matches_keywords(title, raw, PATROCINIO_KEYWORDS):
                continue

            seen_links.add(link)
            items.append({
                "title": title,
                "link": link,
                "image": extract_image(raw),
                "description": extract_text(raw)[:400],
                "date": date,
            })

    # Selezione e sintesi automatica (solo se il servizio è configurato)
    scelti = seleziona_con_ai(category, items)
    if scelti:
        items = scelti
        seen_links = {it["link"] for it in items}
    else:
        items = items[:MAX_ITEMS]
        seen_links = {it["link"] for it in items}

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
