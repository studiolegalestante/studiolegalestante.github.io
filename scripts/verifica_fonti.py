"""Verifica delle fonti candidate per le notizie del sito.
Non pubblica nulla: controlla se ogni fonte è leggibile in automatico
e quante notizie pertinenti alle materie dello studio produce."""
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; verifica-fonti-studio/1.0)"}

FONTI = [
    # nome, gruppo, url (pagina principale o feed)
    ("Gazzetta Ufficiale", "ufficiale", "https://www.gazzettaufficiale.it/"),
    ("Corte costituzionale", "ufficiale", "https://www.cortecostituzionale.it/"),
    ("Corte di cassazione", "ufficiale", "https://www.cortedicassazione.it/"),
    ("EUR-Lex", "ufficiale", "https://eur-lex.europa.eu/content/help/search/predefined-rss.html?locale=it"),
    ("Corte di giustizia UE", "ufficiale", "https://curia.europa.eu/"),
    ("Corte EDU", "ufficiale", "https://www.echr.coe.int/"),
    ("Ministero della Giustizia", "ufficiale", "https://www.giustizia.it/"),
    ("Garante privacy", "ufficiale", "https://www.garanteprivacy.it/"),
    ("Consiglio Nazionale Forense", "ufficiale", "https://www.consiglionazionaleforense.it/"),
    ("Cassa Forense", "ufficiale", "https://www.cassaforense.it/"),
    ("Tribunale di Bari", "ufficiale", "https://tribunale-bari.giustizia.it/"),
    ("Corte d'appello di Bari", "ufficiale", "https://ca-bari.giustizia.it/"),
    ("Camera dei deputati", "ufficiale", "https://www.camera.it/"),
    ("Senato", "ufficiale", "https://www.senato.it/"),
    ("Sistema Penale", "rivista", "https://www.sistemapenale.it/"),
    ("Giustizia Insieme", "rivista", "https://www.giustiziainsieme.it/"),
    ("Questione Giustizia", "rivista", "https://www.questionegiustizia.it/"),
    ("Judicium", "rivista", "https://www.judicium.it/"),
    ("Penale Diritto e Procedura", "rivista", "https://www.penaledp.it/"),
    ("Altalex", "testata", "https://www.altalex.com/"),
    ("Diritto.it", "testata", "https://www.diritto.it/"),
    ("Filodiritto", "testata", "https://www.filodiritto.com/"),
    ("Il Dubbio", "testata", "https://www.ildubbio.news/rss.jsp"),
    ("Studio Cataldi", "testata", "https://feeds2.feedburner.com/studiocataldi/NotizieGiuridiche"),
    ("Avvocato Andreani", "testata", "https://news.avvocatoandreani.it/feed/news_giuridiche.php"),
    ("La Nuova Procedura Civile", "testata", "https://www.lanuovaproceduracivile.com/"),
    ("Il Sole 24 Ore", "testata", "https://www.ilsole24ore.com/"),
    ("ANSA cronaca", "testata", "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml"),
    ("ANSA Puglia", "testata", "https://www.ansa.it/puglia/notizie/puglia_rss.xml"),
    ("Repubblica Bari", "testata", "https://bari.repubblica.it/"),
    ("Corriere del Mezzogiorno", "testata", "https://corrieredelmezzogiorno.corriere.it/"),
    ("BariToday", "testata", "https://www.baritoday.it/"),
    ("La Gazzetta del Mezzogiorno", "testata", "https://www.lagazzettadelmezzogiorno.it/"),
]

MATERIE = {
    "penale": ["reato", "penale", "imputat", "querela", "condann", "pena ", "arresto", "procura", "indagin"],
    "famiglia": ["separazion", "divorz", "affidament", "mantenimento", "figli", "minor", "assegno", "genitor", "coniug"],
    "civile": ["risarciment", "sinistro", "danno", "condomin", "locazion", "contratto", "eredità", "eredit", "responsabilità civile"],
    "patrocinio": ["patrocinio", "spese dello stato", "difesa d'ufficio"],
    "professione": ["avvocat", "forense", "processo telematico", "pct", "deontolog", "cassa forense"],
}
LOCALE = ["bari", "puglia", "triggiano"]


def materie_di(testo):
    t = testo.lower()
    return [m for m, kw in MATERIE.items() if any(k in t for k in kw)]


def scarica(url):
    r = requests.get(url, headers=UA, timeout=25)
    return r.status_code, r.headers.get("content-type", ""), r.content


def feed_da_pagina(base, html):
    """Trova i feed dichiarati nella pagina o linkati con 'rss'/'feed' nell'indirizzo."""
    testo = html.decode("utf-8", "ignore")
    trovati = re.findall(r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', testo, re.I)
    urls = [re.search(r'href=["\']([^"\']+)', t).group(1) for t in trovati if re.search(r'href=["\']([^"\']+)', t)]
    urls += re.findall(r'href=["\']([^"\']*(?:rss|feed)[^"\']*)["\']', testo, re.I)
    visti, out = set(), []
    for u in urls:
        u = urljoin(base, u.replace("&amp;", "&"))
        if u not in visti and u.startswith("http"):
            visti.add(u)
            out.append(u)
    return out[:8]


def analizza_feed(contenuto):
    f = feedparser.parse(contenuto)
    if not f.entries:
        return None
    limite = datetime.now(timezone.utc) - timedelta(days=7)
    recenti = pertinenti = locali = 0
    esempi = []
    for e in f.entries:
        quando = e.get("published_parsed") or e.get("updated_parsed")
        if quando and datetime(*quando[:6], tzinfo=timezone.utc) < limite:
            continue
        recenti += 1
        testo = (e.get("title", "") + " " + e.get("summary", ""))
        mm = materie_di(testo)
        if mm:
            pertinenti += 1
            if len(esempi) < 3:
                esempi.append(f"[{','.join(mm)}] {e.get('title', '')[:90]}")
        if any(k in testo.lower() for k in LOCALE):
            locali += 1
    return {"voci": len(f.entries), "ultimi7gg": recenti, "pertinenti": pertinenti,
            "locali": locali, "esempi": esempi}


risultati = []
for nome, gruppo, url in FONTI:
    esito = {"fonte": nome, "gruppo": gruppo, "url": url}
    try:
        stato, tipo, corpo = scarica(url)
        esito["http"] = stato
        dati = analizza_feed(corpo) if stato == 200 else None
        if dati:
            esito.update(feed=url, **dati)
        elif stato == 200:
            migliori = None
            for fu in feed_da_pagina(url, corpo):
                try:
                    s2, _, c2 = scarica(fu)
                    d2 = analizza_feed(c2) if s2 == 200 else None
                    if d2 and (not migliori or d2["pertinenti"] > migliori[1]["pertinenti"]):
                        migliori = (fu, d2)
                except Exception:
                    pass
                time.sleep(0.5)
            if migliori:
                esito.update(feed=migliori[0], **migliori[1])
            else:
                esito["nota"] = "nessun feed trovato: servirebbe lettura della pagina"
    except Exception as ex:
        esito["errore"] = str(ex)[:120]
    risultati.append(esito)
    riga = f"{nome:30} {gruppo:10} http={esito.get('http', '-'):<4} "
    riga += (f"feed=sì 7gg={esito['ultimi7gg']:<3} pertinenti={esito['pertinenti']:<3} locali={esito['locali']}"
             if "feed" in esito else ("feed=no " + esito.get("nota", esito.get("errore", ""))))
    print(riga)
    for es in esito.get("esempi", []):
        print("      ", es)
    time.sleep(1)

print("RISULTATI_JSON " + json.dumps({"data": datetime.now(timezone.utc).isoformat(), "fonti": risultati}, ensure_ascii=False))
