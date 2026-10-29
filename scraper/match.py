"""Přiřazení akce k jednomu z produktů v products.json."""
import json
import re
from pathlib import Path

from .util import norm

PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "products.json"


def load_products(path=PRODUCTS_FILE):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for p in data["products"]:
        p["_inc"] = [re.compile(x) for x in p["include"]]
        p["_exc"] = [re.compile(x) for x in p["exclude"]]
    return data["products"]


def match(name, products):
    """Vrátí id prvního produktu, kterému název odpovídá, jinak None."""
    text = norm(name)
    for p in products:
        if any(r.search(text) for r in p["_inc"]) and not any(r.search(text) for r in p["_exc"]):
            return p["id"]
    return None


def public_products(products):
    """Seznam produktů pro stránku (bez regulárních výrazů)."""
    return [{"id": p["id"], "label": p["label"], "stems": p["search"]} for p in products]
