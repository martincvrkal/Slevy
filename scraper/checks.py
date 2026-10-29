"""Kontroly, které musí akce projít, než se ukáže na stránce.
Co neprojde, jde do data/ke-kontrole.json s důvodem."""
from .schema import unit_price


def problems(offer, product):
    out = []
    price = offer.get("price")
    if not price or price <= 0:
        out.append("chybí cena")
        return out
    if price > 5000:
        out.append("podezřele vysoká cena")
    orig = offer.get("orig")
    if orig is not None:
        if orig <= price:
            out.append("původní cena není vyšší než akční")
        elif (1 - price / orig) > 0.9:
            out.append("sleva přes 90 %")
    card = offer.get("card")
    if card is not None and card >= price:
        out.append("cena s kartou není nižší")
    f, t = offer.get("from"), offer.get("to")
    if not f or not t:
        out.append("chybí platnost")
    elif f > t:
        out.append("platnost končí dřív, než začne")
    if not offer.get("q") or not offer.get("u"):
        out.append("nepřečtené balení")
    elif product:
        rng = product.get("range", {}).get(offer["u"])
        up = unit_price(offer)
        if rng is None:
            out.append(f"neočekávaná jednotka {offer['u']}")
        elif not (rng[0] <= up <= rng[1]):
            out.append(f"cena {up:.2f} Kč/{offer['u']} mimo rozsah {rng[0]}–{rng[1]}")
    if offer.get("confidence") == "low":
        out.append("model si nebyl jistý přečtením")
    return out
