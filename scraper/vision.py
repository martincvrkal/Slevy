"""Čtení akcí ze stránky letáku pomocí modelu Claude (vision).

Každá stránka se čte jen jednou: výsledek se uloží do data/cache/vision
a příští běh ho použije znovu, takže se neplatí dvakrát."""
import hashlib
import json
import os
import re
from pathlib import Path

from . import http

API_URL = "https://api.anthropic.com/v1/messages"
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache" / "vision"

PROMPT = """Jsi pečlivý přepisovač akčních letáků českých obchodů.
Na obrázku je jedna strana letáku řetězce {chain}. Leták platí od {date_from} do {date_to}.

Vypiš VŠECHNY potraviny a nápoje v akci, které jsou na stránce celé vidět.
Pro každou položku vrať objekt s poli:
- "name": název produktu a značka, jak je v letáku (bez reklamních slov)
- "pack": balení přesně jak je vytištěno, např. "250 g", "1 l", "10 ks", "cena za 1 kg"
- "price": akční cena bez karty jako číslo (29.9). Pokud je cena JEN s kartou nebo aplikací, dej ji sem a vyplň "card_only": true
- "card_price": nižší cena s věrnostní kartou nebo aplikací, jinak null
- "orig": původní (přeškrtnutá) cena jako číslo, jinak null
- "valid_from", "valid_to": data ve tvaru RRRR-MM-DD, pokud u položky stojí jiná platnost než u celého letáku (např. jen o víkendu), jinak null
- "limit": omezení počtu kusů nebo jiná podmínka textem, jinak null
- "confidence": "high", když jsi si jistý cenou i balením, jinak "low"

Nevymýšlej. Když cenu nebo balení nepřečteš jistě, dej confidence "low".
Neuváděj nepotravinové zboží (nářadí, oblečení, drogerie).
Odpověz pouze JSON polem, bez dalšího textu.

Pomocný text ze stránky (může být neúplný a v náhodném pořadí): {hint}
"""


def _cache_path(key):
    return CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".json")


def parse_json_array(text):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError("Odpověď modelu neobsahuje JSON pole")
    data = json.loads(m.group())
    if not isinstance(data, list):
        raise ValueError("Odpověď modelu není pole")
    return data


def read_page(image_url, *, chain, date_from, date_to, hint="", model, api_key=None):
    """Vrátí seznam položek ze stránky. Bez API klíče vrací None."""
    path = _cache_path(f"{model}|{image_url}")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_url}},
                {"type": "text", "text": PROMPT.format(
                    chain=chain, date_from=date_from, date_to=date_to, hint=(hint or "")[:1500])},
            ],
        }],
    }
    resp = http.post_json(API_URL, payload, headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    items = parse_json_array(text)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return items
