"""Accesso al servizio di IA dal workflow GitHub (identità federata, nessuna chiave salvata)."""
import os
import requests

AI = {k: os.environ.get("AI_" + k, "").strip() for k in
      ("BASE", "VERSION", "MODEL", "ORG", "RULE", "ACCOUNT", "WORKSPACE")}
AI_ATTIVA = all(AI.values())
_TOKEN = None


def token_accesso():
    global _TOKEN
    if _TOKEN:
        return _TOKEN
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
    _TOKEN = r.json()["access_token"]
    return _TOKEN


def chiama(model, system, messages, max_tokens=8000, tools=None, timeout=300):
    """Chiamata al servizio; gestisce le pause dei server tool (pause_turn).
    Restituisce (testo finale, usage cumulato)."""
    nome_h, val_h = AI["VERSION"].split("=", 1)
    headers = {"Authorization": "Bearer " + token_accesso(), nome_h: val_h,
               "content-type": "application/json"}
    msgs = list(messages)
    usage = {"input_tokens": 0, "output_tokens": 0, "web_search_requests": 0}
    for _ in range(5):
        body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": msgs}
        if tools:
            body["tools"] = tools
        r = requests.post(AI["BASE"] + "/v1/messages", headers=headers, json=body, timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        d = r.json()
        u = d.get("usage", {})
        usage["input_tokens"] += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
        usage["output_tokens"] += u.get("output_tokens", 0)
        usage["web_search_requests"] += u.get("server_tool_use", {}).get("web_search_requests", 0)
        if d.get("stop_reason") == "pause_turn":
            msgs = msgs + [{"role": "assistant", "content": d["content"]}]
            continue
        testo = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        if not testo:
            print(f"  ⚠️  risposta senza testo (stop: {d.get('stop_reason')}, "
                  f"blocchi: {[b.get('type') for b in d.get('content', [])]})")
        return testo, usage
    raise RuntimeError("troppe pause del server tool")
