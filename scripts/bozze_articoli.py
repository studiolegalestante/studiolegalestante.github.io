"""Genera ogni giorno 2-3 bozze di articoli originali dello studio.
I giornali (data/news.json) servono solo come radar dei temi; il contenuto è scritto
consultando fonti ufficiali. Le bozze vanno nel repo privato studiolegalestante/bozze-articoli e si
pubblicano solo dopo approvazione con scripts/pubblica_articolo.py.
Uso: python scripts/bozze_articoli.py <cartella bozze>"""
import json
import os
import re
import sys

import requests
from datetime import date
from pathlib import Path

from ai_comune import AI, AI_ATTIVA, chiama

N_MIN, N_MAX = 2, 3   # il terzo articolo solo se il tema promette visite e contatti
SOGLIA_TERZO = 4
MODELLO_SCELTA = AI["MODEL"]                                   # Haiku
MODELLO_SCRITTURA = os.environ.get("AI_MODEL_SCRITTURA", "").strip() or AI["MODEL"]
CATEGORIE = {"penale": "diritto-penale.html", "famiglia": "diritto-famiglia.html",
             "civile": "diritto-civile.html", "patrocinio": "patrocinio-spese-stato.html"}

FONTI_UFFICIALI = [
    "cortedicassazione.it", "italgiure.giustizia.it", "cortecostituzionale.it",
    "normattiva.it", "gazzettaufficiale.it", "giustizia.it", "giustizia-amministrativa.it",
    "senato.it", "camera.it", "governo.it", "eur-lex.europa.eu", "curia.europa.eu",
    "hudoc.echr.coe.int", "inps.it", "agenziaentrate.gov.it", "lavoro.gov.it", "garanteprivacy.it",
]


ITALGIURE = "https://www.italgiure.giustizia.it"
SOLR = ITALGIURE + "/sncass/isapi/hc.dll/sn.solr/sn-collection/select?app.query"
# Il server di ItalGiure non invia il certificato intermedio: lo aggiungiamo ai certificati di sistema.
_BUNDLE = None


def bundle_certificati():
    global _BUNDLE
    if _BUNDLE is None:
        import certifi
        import tempfile
        inter = Path(__file__).with_name("certs") / "italgiure-intermedio.pem"
        f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
        f.write(Path(certifi.where()).read_text() + "\n" + inter.read_text())
        f.close()
        _BUNDLE = f.name
    return _BUNDLE


def testo_cassazione(rif):
    """Testo ufficiale di una pronuncia della Cassazione dall'indice pubblico SentenzeWeb."""
    if not rif or not rif.get("numero"):
        return None
    n = str(rif["numero"]).lstrip("0")
    kind = "snpen" if str(rif.get("materia", "")).startswith("pen") else "snciv"
    fq = [f'kind:"{kind}"', f'(numdec:"{n}" OR numdec:"{n.zfill(5)}")']
    if rif.get("anno"):
        fq.append(f'anno:"{rif["anno"]}"')
    dati = [("wt", "json"), ("q", "*:*"), ("rows", "1"),
            ("fl", "id,kind,numdec,anno,datdep,szdec,tipoprov,filename,ocr")] + [("fq", f) for f in fq]
    try:
        r = requests.post(SOLR, data=dati, timeout=30, verify=bundle_certificati(), headers={
            "User-Agent": "Mozilla/5.0 (compatible; studiolegalestante-bozze/1.0)",
            "Referer": ITALGIURE + "/sncass/", "X-Requested-With": "XMLHttpRequest"})
        docs = r.json().get("response", {}).get("docs", [])
    except Exception as e:
        print(f"  ⚠️  ItalGiure non raggiungibile: {e}", file=sys.stderr)
        return None
    if not docs:
        return None
    d = docs[0]
    prima = lambda v: v[0] if isinstance(v, list) else v
    f = prima(d.get("filename")) or ""
    fid = f if ".clean." in f else f.replace(".pdf", ".clean.pdf")
    dep = prima(d.get("datdep")) or ""
    estremi = (f"Cass. {'pen.' if d['kind'] == 'snpen' else 'civ.'}, sez. {d.get('szdec', '')}, "
               f"{str(d.get('tipoprov', '')).lower()} n. {str(d['numdec']).lstrip('0')}"
               + (f" del {dep[6:8]}/{dep[4:6]}/{dep[:4]}" if len(dep) == 8 else ""))
    testo = " ".join(str(prima(d.get("ocr")) or "").split())
    if len(testo) < 1500 or "fase di oscuramento" in testo:
        print(f"  ℹ️  {estremi}: testo non ancora pubblicato su SentenzeWeb")
        return None
    return {"estremi": estremi, "testo": testo[:40000],
            "url": f"{ITALGIURE}/xway/application/nif/clean/hc.dll?verbo=attach&db={d['kind']}&id={fid}"}


def slugify(t):
    t = t.lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"), ("’", "'")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:70].rsplit("-", 1)[0] if len(t) > 70 else t


def estrai_json(testo, aperto="{"):
    chiuso = "}" if aperto == "{" else "]"
    m = re.search(re.escape(aperto) + r".*" + re.escape(chiuso), testo, re.S)
    if not m:
        raise ValueError("risposta senza JSON: " + testo[:150].replace("\n", " "))
    return json.loads(m.group(0))


def temi_gia_trattati(cartella):
    titoli = []
    for p in sorted(Path(cartella).rglob("*.json"))[-80:]:
        try:
            titoli.append(json.loads(p.read_text())["titolo"])
        except Exception:
            pass
    try:
        titoli += [a["titolo"] for a in json.load(open("data/articoli.json"))][-80:]
    except Exception:
        pass
    return titoli


def scegli_temi(radar, gia):
    elenco = "\n".join(f"[{i}] ({r['cat']}) {r['title']} — {r['description'][:250]}"
                       for i, r in enumerate(radar))
    system = (
        "Sei il caporedattore del sito di uno studio legale di Bari (penale, famiglia, civile, "
        "patrocinio a spese dello Stato). Dalla rassegna scegli i temi per "
        f"{N_MAX} articoli originali, in ordine di interesse: privilegia quelli che interessano di più "
        "il pubblico (cittadini con un problema concreto, ricerche frequenti su Google), "
        "trattabili con fonti ufficiali: pronunce della Cassazione con numero, Corte costituzionale, "
        "leggi e decreti; le sentenze dei tribunali vanno bene solo come spunto per un tema generale. "
        "Evita temi già trattati, tecnicismi per soli avvocati e temi uguali tra loro. "
        "Rispondi solo con JSON: [{\"n\": <numero>, \"categoria\": \"penale|famiglia|civile|patrocinio\", "
        "\"angolo\": \"<domanda del cittadino a cui l'articolo risponde>\", "
        "\"ricerca\": \"<estremi da cercare nelle fonti ufficiali>\", "
        "\"cassazione\": {\"materia\": \"civile|penale\", \"numero\": \"<numero>\", \"anno\": \"<anno>\"} oppure null, "
        "\"interesse\": <1-5: visite e richieste di contatto che il tema può portare a uno studio legale>}]")
    utente = elenco + "\n\nGià trattati:\n" + ("\n".join(gia) or "nessuno")
    for tentativo in range(2):
        testo, usage = chiama(MODELLO_SCELTA, system, [{"role": "user", "content": utente}], 8000)
        try:
            return estrai_json(testo, "["), usage
        except ValueError as e:
            print(f"  ⚠️  scelta temi, tentativo {tentativo + 1}: {e}", file=sys.stderr)
    raise RuntimeError("scelta dei temi non riuscita")


SISTEMA_SCRITTURA = """Scrivi un articolo originale per il sito dello Studio Legale Avv. Vincenzo Stante (Bari).
Regole:
- Fonti: usa lo strumento di ricerca, che consulta solo siti istituzionali. Ogni fatto (numero della sentenza, data, contenuto, norma) deve risultare da una fonte ufficiale trovata. L'articolo di giornale indicato è solo lo spunto: non usarlo come fonte e non riprenderne frasi o struttura.
- Se ti viene fornito il testo ufficiale di una pronuncia della Cassazione, è la fonte principale: riassumila con parole tue (fatti essenziali, principio affermato, conseguenze pratiche).
- Se la pronuncia citata nello spunto non è disponibile né si trova nelle fonti ufficiali, non nominarla: rispondi comunque alla domanda del cittadino con le norme e le pronunce ufficiali che trovi.
- Solo se non trovi alcuna base ufficiale per rispondere, rispondi {"scarta": true, "motivo": "..."}.
- Pubblico: cittadini, non avvocati. Italiano chiaro, frasi brevi, si dà del voi. Tono professionale e rassicurante, senza enfasi.
- Lunghezza 600-900 parole. Struttura: apertura di 2-3 frasi con la risposta in sintesi; 3-5 sezioni <h2> con titoli in forma di domanda o di azione; una sezione finale "Cosa fare in pratica" con un elenco.
- Niente commenti sul lavoro di ricerca ("la sintesi consultata", "secondo un documento"): scrivi i fatti e indica la fonte per nome (es. "la Cassazione, con la sentenza n. ...").
- Quando citi un articolo di legge spiega in poche parole cosa prevede.
- Non inventare nulla, non dare consigli sul caso concreto, non promettere risultati, niente inviti a contattare lo studio (li aggiunge il sito).
- HTML ammesso nel corpo: h2, h3, p, ul, ol, li, strong, em. Nessun link nel corpo.
- Titolo SEO di massimo 65 caratteri con la parola chiave che un cittadino cercherebbe; descrizione di massimo 155 caratteri.
Rispondi SOLO con JSON:
{"titolo": "...", "sottotitolo": "<una frase>", "descrizione": "...", "parola_chiave": "...",
 "corpo_html": "...", "faq": [{"domanda": "...", "risposta": "..."}] (2-3),
 "fonti": [{"titolo": "...", "url": "<url ufficiale effettivamente consultato>"}]}"""


def scrivi(tema, spunto):
    sentenza = testo_cassazione(tema.get("cassazione"))
    strumenti = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2 if sentenza else 3,
                  "allowed_domains": FONTI_UFFICIALI}]
    utente = (f"Categoria: {tema['categoria']}\nDomanda del cittadino: {tema['angolo']}\n"
              f"Da cercare nelle fonti ufficiali: {tema['ricerca']}\n"
              f"Spunto (solo radar, non fonte): {spunto['title']} — {spunto['link']}")
    if sentenza:
        utente += (f"\n\nTesto ufficiale (SentenzeWeb, OCR) di {sentenza['estremi']} — url {sentenza['url']}:\n"
                   + sentenza["testo"])
        print(f"  📄 {sentenza['estremi']} ({len(sentenza['testo'])} caratteri)")
    testo, usage = chiama(MODELLO_SCRITTURA, SISTEMA_SCRITTURA,
                          [{"role": "user", "content": utente}], 8000, strumenti)
    return estrai_json(testo), usage


def costo(u, modello):
    prezzi = {"haiku": (0.10, 0.50), "sonnet": (2.0, 10.0), "opus": (4.0, 20.0)}
    pi, po = next((v for k, v in prezzi.items() if k in modello), (2.0, 10.0))
    return round(u["input_tokens"] / 1e6 * pi + u["output_tokens"] / 1e6 * po
                 + u.get("web_search_requests", 0) * 0.01, 4)


def main():
    if not AI_ATTIVA:
        sys.exit("servizio IA non configurato")
    cartella = Path(sys.argv[1] if len(sys.argv) > 1 else "bozze")
    oggi = date.today().isoformat()
    radar = [dict(a, cat=c) for c, v in json.load(open("data/news.json")).items() for a in v]
    temi, u_scelta = scegli_temi(radar, temi_gia_trattati(cartella))
    spesa = costo(u_scelta, MODELLO_SCELTA)
    print(f"Temi scelti: {len(temi)} (costo scelta {spesa} $)")
    (cartella / oggi).mkdir(parents=True, exist_ok=True)
    fatti = 0
    temi = sorted(temi, key=lambda t: -int(t.get("interesse", 0)))[:N_MAX]
    temi = temi[:N_MIN] + [t for t in temi[N_MIN:] if int(t.get("interesse", 0)) >= SOGLIA_TERZO]
    for tema in temi:
        spunto = radar[int(tema["n"])]
        try:
            art, u = scrivi(tema, spunto)
        except Exception as e:
            print(f"  ❌ {tema['angolo']}: {e}", file=sys.stderr)
            continue
        c = costo(u, MODELLO_SCRITTURA)
        spesa += c
        if art.get("scarta"):
            print(f"  ⏭️  scartato: {tema['angolo']} ({art.get('motivo', '')}) — {c} $")
            continue
        if not art.get("fonti"):
            print(f"  ⏭️  senza fonti, scartato: {art.get('titolo')}")
            continue
        art.update(slug=slugify(art["titolo"]), categoria=tema["categoria"], data=oggi,
                   interesse=tema.get("interesse"),
                   radar={"titolo": spunto["title"], "link": spunto["link"]},
                   modello=MODELLO_SCRITTURA, costo_usd=c, stato="bozza")
        (cartella / oggi / f"{art['slug']}.json").write_text(
            json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
        fatti += 1
        print(f"  ✅ {art['titolo']} — {c} $ ({u['web_search_requests']} ricerche)")
    print(f"Bozze create: {fatti}; costo totale stimato {round(spesa, 3)} $")


if __name__ == "__main__":
    main()
