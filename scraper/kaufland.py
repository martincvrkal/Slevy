"""Kaufland: celý týdenní přehled akcí je přímo v HTML stránky nabídky
(objekt window.SSR) a web zvlášť dává seznam čísel zboží platných
v konkrétní prodejně. Z obojího vznikne nabídka pro prodejny v okolí."""
import json
import re

from . import http
from .schema import make_offer
from .util import distance_km, parse_pack, price_cz

BASE = "https://prodejny.kaufland.cz"
OVERVIEW = BASE + "/nabidka/prehled.html?kloffer-week={week}"
STORES = BASE + "/.klstorefinder.json"
STORE_OFFERS = BASE + "/.kloffers.storeName={store}.json"
CARD = "Kaufland Card XTRA"


def extract_ssr(html):
    """Najde JSON za `window.SSR['…'] = ` až po </script>."""
    m = re.search(r"window\.SSR\['[^']+'\]\s*=\s*", html)
    if not m:
        raise ValueError("Kaufland: na stránce chybí window.SSR – změnil se web?")
    start = m.end()
    end = html.index("</script>", start)
    body = html[start:end].strip().rstrip(";")
    return json.loads(body)


def walk_offers(node):
    """Projde libovolně zanořená data a vrátí všechny objekty s offerId."""
    found = {}

    def walk(n):
        if isinstance(n, dict):
            if "offerId" in n and "klNr" in n:
                found[n["offerId"]] = n
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    return list(found.values())


def to_offer(raw, store_ids):
    name = " ".join(x for x in [raw.get("title"), raw.get("subtitle")] if x)
    price = raw.get("price")
    card = price_cz(raw.get("loyaltyFormattedPrice"))
    if card is not None and price is not None and card >= price:
        card = None
    limit = None
    unit_text = raw.get("unit") or ""
    if "pult" in (raw.get("subtitle") or "").lower():
        limit = "Jen u masového pultu"
    return make_offer(
        chain="kaufland",
        name=name.replace("\n", " "),
        price=price,
        orig=price_cz(raw.get("formattedOldPrice")),
        pct=raw.get("discount") or None,
        card=card,
        date_from=raw.get("dateFrom"),
        date_to=raw.get("dateTo"),
        pack=parse_pack(unit_text),
        limit=limit,
        stores=store_ids,
        source="kaufland-web",
        url=BASE + "/nabidka/prehled.html",
        raw_id=raw.get("klNr"),
    )


def area_stores(center, radius_km):
    stores = http.get_json(STORES)
    result = []
    for s in stores:
        try:
            lat, lng = float(s["lat"]), float(s["lng"])
        except (KeyError, ValueError):
            continue
        if distance_km(center["lat"], center["lng"], lat, lng) <= radius_km:
            result.append({
                "id": "kaufland:" + s["n"],
                "code": s["n"],
                "chain": "kaufland",
                "where": f'{s.get("t", "")}, {s.get("sn", "")}'.strip(", "),
                "lat": lat,
                "lng": lng,
            })
    return result


def build(raw_offers, store_lists):
    """raw_offers: z extract_ssr; store_lists: {branch_id: set(klNr)}"""
    offers = []
    for raw in raw_offers:
        ids = sorted(b for b, nrs in store_lists.items() if raw.get("klNr") in nrs)
        if not ids:
            continue
        offers.append(to_offer(raw, ids))
    return offers


def scrape(center, radius_km, log=print):
    branches = area_stores(center, radius_km)
    log(f"Kaufland: {len(branches)} prodejen v okolí")
    store_lists = {}
    for b in branches:
        rows = http.get_json(STORE_OFFERS.format(store=b["code"]))
        store_lists[b["id"]] = {r["klNr"] for r in rows}
    raw = {}
    for week in ("current", "next"):
        try:
            data = extract_ssr(http.get(OVERVIEW.format(week=week)))
        except Exception as e:  # další týden ještě nemusí být zveřejněný
            log(f"Kaufland ({week}): {e}")
            continue
        for o in walk_offers(data.get("props", {}).get("offerData", {})):
            raw[o["offerId"]] = o
    raw = list(raw.values())
    offers = build(raw, store_lists)
    log(f"Kaufland: {len(raw)} akcí na webu, {len(offers)} platí v okolí")
    for b in branches:
        b.pop("code", None)
    return offers, branches
