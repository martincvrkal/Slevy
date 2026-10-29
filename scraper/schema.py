"""Jednotný tvar akce, do kterého převádí všechny zdroje."""


def make_offer(*, chain, name, price, date_from, date_to, source, pack=None,
               orig=None, pct=None, card=None, limit=None, stores=None, only=None,
               url=None, raw_id=None):
    """Vrátí slovník jedné akce.

    pack: (množství, 'kg'|'l'|'ks', cena_za_jednotku) z util.parse_pack
    stores: seznam id prodejen, kde akce platí (None = všechny prodejny řetězce)
    only: 'hyper' / 'super' – omezení na typ prodejny
    """
    q, u, per_unit = pack if pack else (None, None, False)
    if orig is not None and price and orig > price and pct is None:
        pct = round((1 - price / orig) * 100)
    return {
        "chain": chain,
        "name": " ".join(name.split()),
        "price": round(float(price), 2) if price is not None else None,
        "orig": round(float(orig), 2) if orig else None,
        "pct": pct or None,
        "card": round(float(card), 2) if card else None,
        "q": q,
        "u": u,
        "perUnit": bool(per_unit),
        "from": date_from,
        "to": date_to,
        "limit": limit,
        "stores": stores,
        "only": only,
        "source": source,
        "url": url,
        "rawId": raw_id,
    }


def unit_price(offer):
    if not offer.get("q") or not offer.get("price"):
        return None
    return offer["price"] / offer["q"]
