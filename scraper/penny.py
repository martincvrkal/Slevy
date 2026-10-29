"""Penny: web má malý výběr akcí z letáku ve strukturované podobě
(kategorie „Web od …“) a veřejný seznam prodejen se souřadnicemi.
Zbytek letáku se musí číst z obrázků (zatím není hotové)."""
from . import http
from .schema import make_offer
from .util import distance_km, parse_pack

BASE = "https://www.penny.cz"
TREE = BASE + "/api/product-discovery/categories/tree"
PRODUCTS = BASE + "/api/product-discovery/categories/{slug}/products?page={page}&pageSize=50"
STORES = BASE + "/api/stores"


def web_slugs(tree):
    """Najde kategorie typu 'web-od-29102026' (jedna na každý leták)."""
    slugs = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            slug = n.get("slug") or ""
            if slug.startswith("web-od-") and slug.count("-") == 2:
                slugs.append(slug)
            for key in ("children", "subcategories", "categories"):
                walk(n.get(key))

    walk(tree)
    return slugs


def to_offer(p):
    price = p.get("price") or {}
    regular = price.get("regular") or {}
    loyalty = price.get("loyalty") or {}
    value = regular.get("value")
    if value is None:
        return None
    unit = p.get("volumeLabelShort") or p.get("packageLabelKey") or ""
    if p.get("weightArticle"):
        pack = (1.0, "kg", True)
    else:
        pack = parse_pack(f'{p.get("amount", "")} {unit}')
    card = loyalty.get("value")
    return make_offer(
        chain="penny",
        name=p.get("name", ""),
        price=value / 100,
        orig=(price.get("crossed") or 0) / 100 or None,
        card=card / 100 if card and card < value else None,
        date_from=price.get("validityStart"),
        date_to=price.get("validityEnd"),
        pack=pack,
        source="penny-web",
        url=BASE + "/nabidky",
        raw_id=p.get("sku"),
    )


def fetch_products(slug):
    page, items = 0, []
    while True:
        data = http.get_json(PRODUCTS.format(slug=slug, page=page))
        results = data.get("results") or []
        items.extend(results)
        if not results or len(items) >= data.get("total", 0) or page > 20:
            return items
        page += 1


def area_stores(center, radius_km):
    result = []
    for s in http.get_json(STORES):
        pos = s.get("position") or {}
        if "lat" not in pos:
            continue
        if distance_km(center["lat"], center["lng"], pos["lat"], pos["lng"]) <= radius_km:
            result.append({
                "id": "penny:" + s["storeId"].lstrip("#"),
                "chain": "penny",
                "where": f'{s.get("city", "")}, {s.get("street", "")}'.strip(", "),
                "lat": pos["lat"],
                "lng": pos["lng"],
            })
    return result


def scrape(center, radius_km, log=print):
    branches = area_stores(center, radius_km)
    log(f"Penny: {len(branches)} prodejen v okolí")
    offers = []
    for slug in web_slugs(http.get_json(TREE)):
        items = fetch_products(slug)
        log(f"Penny: {slug} – {len(items)} akcí na webu")
        offers.extend(o for o in (to_offer(p) for p in items) if o)
    return offers, branches
