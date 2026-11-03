"""Scarica dall'ISTAT gli indici FOI senza tabacchi (mensili, Italia) e li salva in data/foi.json."""
import csv
import io
import json
import sys
import urllib.request

BASE = "https://esploradati.istat.it/SDMXWS/rest/data/IT1,{df},1.0/all?startPeriod={da}"
HDR = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0", "User-Agent": "indici-foi-studio/1.0"}


def scarica(df, da):
    req = urllib.request.Request(BASE.format(df=df, da=da), headers=HDR)
    with urllib.request.urlopen(req, timeout=300) as r:
        testo = r.read().decode("utf-8-sig", "ignore")
    righe = list(csv.DictReader(io.StringIO(testo)))
    out = {}
    for r in righe:
        voce = r.get("ECOICOP_2") or r.get("E_COICOP_REV_ISTAT")
        if r.get("REF_AREA") == "IT" and r.get("MEASURE") == "4" and voce == "00ST" and r.get("OBS_VALUE"):
            out[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    return out


def base_di(periodo):
    anno = int(periodo[:4])
    return 1995 if anno <= 2010 else 2010 if anno <= 2015 else 2015 if anno <= 2025 else 2025


storico = scarica("169_748_DF_DCSP_FOI1B2025_2", "1996-01")
recenti = scarica("169_748", "2026-01")
indici = {p: [v, base_di(p)] for p, v in sorted({**storico, **{k: v for k, v in recenti.items() if k >= "2026-01"}}.items())}
if len(indici) < 300 or "2009-01" not in indici:
    sys.exit(f"Dati incompleti: {len(indici)} mesi")
print("controllo 2009-01:", indici["2009-01"], "atteso 134.2 base 1995")
print("controllo ultimo:", max(indici), indici[max(indici)])
json.dump({
    "fonte": "ISTAT, indice FOI senza tabacchi",
    "raccordo": {"1995": 1.3731, "2010": 1.071, "2015": 1.214},
    "indici": indici,
}, open("data/foi.json", "w"), separators=(",", ":"))
print("mesi salvati:", len(indici))
