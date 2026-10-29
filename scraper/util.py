"""Pomocné funkce: normalizace textu, balení, ceny, vzdálenost."""
import math
import re
import unicodedata


def norm(text):
    """Malá písmena, bez diakritiky, jedna mezera."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def price_cz(text):
    """'29,90' -> 29.9 ; '1 299,00' -> 1299.0 ; prázdné -> None"""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    t = text.replace(" ", "").replace(" ", "").replace(",", ".")
    m = re.search(r"\d+(\.\d+)?", t)
    return float(m.group()) if m else None


_UNITS = {
    "kg": ("kg", 1.0), "g": ("kg", 0.001), "dkg": ("kg", 0.01),
    "l": ("l", 1.0), "ml": ("l", 0.001), "cl": ("l", 0.01), "dl": ("l", 0.1),
    "ks": ("ks", 1.0), "kus": ("ks", 1.0), "kusy": ("ks", 1.0), "kusu": ("ks", 1.0),
    "kusů": ("ks", 1.0), "st": ("ks", 1.0),
}


def parse_pack(text):
    """Rozloží balení na (množství, jednotka, je_cena_za_kilo).

    '250 g' -> (0.25, 'kg', False)
    '3x35 g' -> (0.105, 'kg', False)
    '5 kg balení' -> (5.0, 'kg', False)
    'cena za 1 kg' -> (1.0, 'kg', True)
    '180 g/200 g' -> (0.18, 'kg', False)  # bere se první varianta
    '10 ks' -> (10.0, 'ks', False)
    Vrací None, když balení nejde přečíst.
    """
    if not text:
        return None
    t = norm(text).replace(",", ".")
    per_unit = "cena za" in t or t.startswith("za ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|dkg|g|ml|cl|dl|l|ks)\b", t)
    if m:
        count, size, unit = float(m.group(1)), float(m.group(2)), m.group(3)
        base, factor = _UNITS[unit]
        return (round(count * size * factor, 6), base, False)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|dkg|g|ml|cl|dl|l|kusu|kusy|kus|ks)\b", t)
    if m:
        qty, unit = float(m.group(1)), m.group(2)
        base, factor = _UNITS[unit]
        return (round(qty * factor, 6), base, per_unit)
    if re.search(r"\b(kus|ks)\b", t):
        return (1.0, "ks", False)
    return None


def distance_km(a_lat, a_lng, b_lat, b_lng):
    r = math.pi / 180
    dlat, dlng = (b_lat - a_lat) * r, (b_lng - a_lng) * r
    h = math.sin(dlat / 2) ** 2 + math.cos(a_lat * r) * math.cos(b_lat * r) * math.sin(dlng / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
