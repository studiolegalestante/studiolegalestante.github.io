"""Pubblica una bozza approvata come pagina indicizzabile in articoli/<slug>.html,
aggiorna data/articoli.json, l'indice articoli/index.html e la sitemap.
Uso: python scripts/pubblica_articolo.py <bozza.json>  (dalla radice del sito)"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

SITO = "https://www.studiolegalestante.it"
MODELLO = Path("guida-informazione-di-garanzia.html")   # da qui si copiano testata e piè di pagina
MESI = "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split()
CATEGORIE = {"penale": ("diritto-penale.html", "Diritto penale"),
             "famiglia": ("diritto-famiglia.html", "Famiglia e minori"),
             "civile": ("diritto-civile.html", "Civile, casa e crediti"),
             "patrocinio": ("patrocinio-spese-stato.html", "Patrocinio a spese dello Stato")}
e = html.escape


def data_it(iso):
    a, m, g = iso.split("-")
    return f"{int(g)} {MESI[int(m) - 1]} {a}"


def un_livello_su(frammento):
    """Corregge i collegamenti relativi per una pagina dentro articoli/."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"(https?:|/|#|tel:|mailto:|\.\./)", url):
            return m.group(0)
        url = url[2:] if url.startswith("./") else url
        return f'{attr}="../{url}"'
    return re.sub(r'(href|src)="([^"]*)"', fix, frammento)


def parti_modello():
    t = MODELLO.read_text(encoding="utf-8")
    testata = re.search(r'<header class="contenitore testata">.*?</header>', t, re.S).group(0)
    pie = re.search(r'<footer class="pie">.*?</body>', t, re.S).group(0)
    return un_livello_su(testata), un_livello_su(pie)


def ld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=1) + "\n</script>"


def testa(titolo, descr, url, tipo="article", extra=""):
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titolo)} | Avv. Stante</title>
<meta name="description" content="{e(descr)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#1D2B45">
<link rel="icon" href="../favicon.svg?v=20261029" type="image/svg+xml">
<link rel="apple-touch-icon" href="../apple-touch-icon.png?v=20261029">
<link rel="preload" href="../assets/fonts/libre-caslon-display-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../assets/fonts/libre-caslon-text-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../assets/css/studio.css?v=20261114b">
<meta property="og:type" content="{tipo}">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="Studio Legale Avv. Vincenzo Stante">
<meta property="og:title" content="{e(titolo)}">
<meta property="og:description" content="{e(descr)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITO}/images/og-studio-stante.jpg">
<meta name="twitter:card" content="summary_large_image">
{extra}
</head>
<body>
<a class="salta" href="#contenuto">Vai al contenuto</a>
"""


def pagina_articolo(a, testata, pie):
    url = f"{SITO}/articoli/{a['slug']}.html"
    cat_url, cat_nome = CATEGORIE.get(a["categoria"], ("guide.html", "Guide"))
    briciole = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITO + "/"},
        {"@type": "ListItem", "position": 2, "name": "Approfondimenti", "item": SITO + "/articoli/"},
        {"@type": "ListItem", "position": 3, "name": a["titolo"], "item": url}]})
    articolo = ld({"@context": "https://schema.org", "@type": "Article", "headline": a["titolo"],
                   "description": a["descrizione"], "inLanguage": "it",
                   "datePublished": a["data"], "dateModified": a["data"],
                   "author": {"@type": "Person", "name": "Avv. Vincenzo Stante", "url": SITO + "/"},
                   "publisher": {"@id": SITO + "/#studio"}, "mainEntityOfPage": url})
    faq = a.get("faq") or []
    extra = briciole + "\n" + articolo
    if faq:
        extra += "\n" + ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["domanda"],
             "acceptedAnswer": {"@type": "Answer", "text": f["risposta"]}} for f in faq]})
    faq_html = ""
    if faq:
        faq_html = '<h2 id="domande">Domande frequenti</h2>\n<div class="faq">\n' + "\n".join(
            f"<details><summary>{e(f['domanda'])}</summary><div>{e(f['risposta'])}</div></details>"
            for f in faq) + "\n</div>"
    fonti = "\n".join(f'<li><a href="{e(f["url"])}" rel="noopener" target="_blank">{e(f["titolo"])}</a></li>'
                      for f in a["fonti"])
    return testa(a["titolo"], a["descrizione"], url, extra=extra) + testata + f"""

<main id="contenuto">
  <div class="contenitore pagina-titolo">
    <nav class="percorso" aria-label="Percorso"><ol><li><a href="../">Home</a></li><li><a href="./">Approfondimenti</a></li><li aria-current="page">{e(a['titolo'])}</li></ol></nav>
    <h1>{e(a['titolo'])}</h1>
    <p>{e(a.get('sottotitolo', ''))}</p>
    <p class="data">A cura dell'Avv. Vincenzo Stante. Pubblicato il {data_it(a['data'])}.</p>
  </div>

  <div class="contenitore sezione">
    <div class="prosa">
{a['corpo_html']}
{faq_html}
      <div class="chiusura">
        <h2>Una valutazione sui vostri documenti</h2>
        <p>Con la consulenza online esamino gli atti e i documenti del vostro caso e vi invio un parere scritto su come stanno le cose e cosa conviene fare. Prezzo fisso, comunicato prima di iniziare.</p>
        <p class="prezzo-chiusura">Ordinaria 150 €, entro 5 giorni lavorativi; urgente 250 €, entro 2 giorni lavorativi. Più spese generali, Cassa e bollo.</p>
        <div class="azioni a-sinistra">
          <a class="bottone pieno" href="../consulenza-online.html#richiesta">Richiedi una consulenza online</a>
          <a class="bottone vuoto" href="tel:+393401834145">Chiama lo studio</a>
        </div>
      </div>
<h2>Fonti</h2>
<ul class="correlati">
{fonti}
</ul>
<h2>Da leggere anche</h2>
<ul class="correlati"><li><a href="../{cat_url}">{cat_nome}</a></li><li><a href="./">Tutti gli approfondimenti</a></li></ul>
      <p class="avvertenza">Le informazioni di questa pagina sono di carattere generale e non sostituiscono un parere sul caso concreto, che dipende dagli atti e dai fatti specifici.</p>
    </div>
  </div>
</main>

""" + pie + "\n</html>\n"


def pagina_indice(elenco, testata, pie):
    url = SITO + "/articoli/"
    voci = "\n".join(
        f'<li><a href="{x["slug"]}.html">{e(x["titolo"])}</a><br><span class="data">{data_it(x["data"])}</span> — {e(x["descrizione"])}</li>'
        for x in sorted(elenco, key=lambda x: x["data"], reverse=True))
    descr = "Approfondimenti dello Studio Legale Avv. Vincenzo Stante su sentenze e novità di diritto penale, famiglia e civile, spiegate in modo chiaro."
    return testa("Approfondimenti legali", descr, url, "website") + testata + f"""

<main id="contenuto">
  <div class="contenitore pagina-titolo">
    <nav class="percorso" aria-label="Percorso"><ol><li><a href="../">Home</a></li><li aria-current="page">Approfondimenti</li></ol></nav>
    <h1>Approfondimenti</h1>
    <p>Sentenze e novità di legge spiegate dallo studio, con le fonti ufficiali.</p>
  </div>
  <div class="contenitore sezione">
    <div class="prosa">
<ul class="correlati">
{voci}
</ul>
      <p><a href="../news.html">Rassegna stampa giornaliera</a></p>
    </div>
  </div>
</main>

""" + pie + "\n</html>\n"


def aggiorna_sitemap(urls):
    p = Path("sitemap.xml")
    s = p.read_text(encoding="utf-8")
    oggi = date.today().isoformat()
    for u in urls:
        riga = f"  <url><loc>{u}</loc><lastmod>{oggi}</lastmod></url>"
        if f"<loc>{u}</loc>" in s:
            s = re.sub(rf"  <url><loc>{re.escape(u)}</loc>.*?</url>", riga, s)
        else:
            s = s.replace("</urlset>", riga + "\n</urlset>")
    p.write_text(s, encoding="utf-8")


def main():
    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for k in ("titolo", "slug", "descrizione", "corpo_html", "fonti", "data", "categoria"):
        if not a.get(k):
            sys.exit(f"campo mancante: {k}")
    if re.search(r"cite\b|index=", a["corpo_html"] + json.dumps(a.get("faq", []))):
        sys.exit("la bozza contiene ancora marcatori di citazione")
    testata, pie = parti_modello()
    Path("articoli").mkdir(exist_ok=True)
    Path(f"articoli/{a['slug']}.html").write_text(pagina_articolo(a, testata, pie), encoding="utf-8")
    reg = Path("data/articoli.json")
    elenco = json.loads(reg.read_text()) if reg.exists() else []
    elenco = [x for x in elenco if x["slug"] != a["slug"]] + [
        {k: a[k] for k in ("titolo", "slug", "data", "categoria", "descrizione")}]
    reg.write_text(json.dumps(elenco, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("articoli/index.html").write_text(pagina_indice(elenco, testata, pie), encoding="utf-8")
    aggiorna_sitemap([SITO + "/articoli/", f"{SITO}/articoli/{a['slug']}.html"])
    print(f"Pubblicato: articoli/{a['slug']}.html")


if __name__ == "__main__":
    main()
