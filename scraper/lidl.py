"""Lidl: potraviny jsou jen v letáku. Leták i jeho stránky (obrázky
a pomocný text) dává veřejné rozhraní platformy leaflets.schwarz.
Akce ze stránek čte model Claude (scraper/vision.py)."""
import re

from . import http, vision
from .schema import make_offer
from .util import parse_pack

LIST_PAGE = "https://www.lidl.cz/c/akcni-letak/s10008644"
FLYER_API = ("https://endpoints.leaflets.schwarz/v4/flyer?flyer_identifier={fid}"
             "&region_id=0&region_code=0")
FOOD_PREFIX = "akcni-letak-od-"


def flyer_ids(html):
    ids = re.findall(r"/l/cs/letak/([a-z0-9-]+)/ar/0", html)
    seen, result = set(), []
    for fid in ids:
        if fid.startswith(FOOD_PREFIX) and fid not in seen:
            seen.add(fid)
            result.append(fid)
    return result


def items_to_offers(items, flyer, page_no):
    offers = []
    fid = flyer.get("name") or flyer.get("id")
    for it in items or []:
        price = it.get("price")
        if not price or not it.get("name"):
            continue
        card = it.get("card_price")
        limit = it.get("limit")
        if it.get("card_only"):
            limit = "Cena platí jen s aplikací Lidl Plus" + (f". {limit}" if limit else "")
        offer = make_offer(
            chain="lidl",
            name=it["name"],
            price=price,
            orig=it.get("orig"),
            card=card if card and card < price else None,
            date_from=it.get("valid_from") or flyer.get("offerStartDate"),
            date_to=it.get("valid_to") or flyer.get("offerEndDate"),
            pack=parse_pack(it.get("pack") or ""),
            limit=limit,
            source="lidl-letak",
            url=flyer.get("flyerUrlAbsolute"),
            raw_id=f"{fid}#s{page_no}",
        )
        offer["confidence"] = it.get("confidence", "low")
        offers.append(offer)
    return offers


def scrape(model, max_pages, log=print):
    offers, pages_read, skipped = [], 0, 0
    for fid in flyer_ids(http.get(LIST_PAGE)):
        flyer = http.get_json(FLYER_API.format(fid=fid)).get("flyer") or {}
        log(f'Lidl: leták {fid} ({flyer.get("offerStartDate")}–{flyer.get("offerEndDate")}), '
            f'{len(flyer.get("pages", []))} stran')
        for page in flyer.get("pages", []):
            if page.get("pageType") not in (None, "page"):
                continue
            if pages_read >= max_pages:
                skipped += 1
                continue
            items = vision.read_page(
                page.get("zoom") or page.get("image"),
                chain="Lidl",
                date_from=flyer.get("offerStartDate"),
                date_to=flyer.get("offerEndDate"),
                hint=page.get("keyWords", ""),
                model=model,
            )
            if items is None:
                log("Lidl: chybí ANTHROPIC_API_KEY, leták se nečte")
                return offers
            pages_read += 1
            offers.extend(items_to_offers(items, flyer, page.get("number")))
    if skipped:
        log(f"Lidl: {skipped} stran přeskočeno kvůli limitu na jeden běh")
    return offers
