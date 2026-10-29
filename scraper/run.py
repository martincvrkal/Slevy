"""Denní běh: stáhne akce ze všech zdrojů, spáruje je s produkty,
zkontroluje a zapíše data pro stránku.

Spuštění:  python -m scraper.run
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import kaufland, lidl, penny
from .checks import problems
from .match import load_products, match, public_products
from .util import distance_km

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "akce.json"
REVIEW = ROOT / "data" / "ke-kontrole.json"
STATUS = ROOT / "data" / "stav.json"
HISTORY_DAYS = 21  # jak dlouho držet skončené akce kvůli „naposledy v akci“
DROP_ALERT = 0.5   # pokles počtu akcí zdroje pod polovinu = varování


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def offer_key(o):
    return f'{o["chain"]}|{o.get("rawId")}|{o.get("from")}|{o.get("to")}|{o.get("name")}'


def run(today=None, sources=None):
    today = today or date.today().isoformat()
    config = load_json(ROOT / "config.json", {})
    area = config["area"]
    products = load_products()
    by_id = {p["id"]: p for p in products}
    previous = load_json(OUT, {"offers": [], "branches": []})
    prev_status = load_json(STATUS, {}).get("sources", {})

    branches = [b for b in load_json(ROOT / "branches_static.json", {}).get("branches", [])
                if distance_km(area["center"]["lat"], area["center"]["lng"], b["lat"], b["lng"]) <= area["radius_km"]]
    raw, status, log_lines = [], {}, []

    def log(msg):
        print(msg)
        log_lines.append(msg)

    runners = sources or {
        "kaufland": lambda: kaufland.scrape(area["center"], area["radius_km"], log),
        "penny": lambda: penny.scrape(area["center"], area["radius_km"], log),
        "lidl": lambda: (lidl.scrape(config["vision"]["model"], config["vision"]["max_pages_per_run"], log), []),
    }
    for name, fn in runners.items():
        try:
            offers, found_branches = fn()
            branches.extend(found_branches)
            raw.extend(offers)
            count = len(offers)
            before = prev_status.get(name, {}).get("count", 0)
            warn = None
            if before and count < before * DROP_ALERT:
                warn = f"počet akcí klesl z {before} na {count}"
            status[name] = {"ok": True, "count": count, "warning": warn}
            if warn:
                log(f"VAROVÁNÍ {name}: {warn}")
        except Exception as e:  # jeden rozbitý zdroj nesmí shodit ostatní
            log(f"CHYBA {name}: {e}")
            status[name] = {"ok": False, "count": 0, "error": str(e)}

    # zdroje, které selhaly, převezmou z minula akce, které ještě platí
    failed = {n for n, s in status.items() if not s["ok"] or s["count"] == 0}
    carried = [o for o in previous.get("offers", []) if o["chain"] in failed and o["to"] >= today]
    if carried:
        log(f"Převzato z minulého běhu: {len(carried)} platných akcí ({', '.join(sorted(failed))})")
    if failed:
        known = {b["id"] for b in branches}
        branches.extend(b for b in previous.get("branches", []) if b["chain"] in failed and b["id"] not in known)

    good, review = [], []
    for o in raw:
        pid = match(o["name"], products)
        if not pid:
            continue
        o["p"] = pid
        issues = problems(o, by_id[pid])
        if issues:
            review.append({**o, "problems": issues})
        else:
            good.append(o)
    good.extend(carried)

    # historie: skončené akce z posledních týdnů, které už zdroj neuvádí
    cutoff = (date.fromisoformat(today) - timedelta(days=HISTORY_DAYS)).isoformat()
    keys = {offer_key(o) for o in good}
    history = [o for o in previous.get("offers", [])
               if o["to"] < today and o["to"] >= cutoff and offer_key(o) not in keys]
    good.extend(history)

    # prodejny bez duplicit
    seen, uniq = set(), []
    for b in branches:
        if b["id"] not in seen:
            seen.add(b["id"])
            uniq.append(b)

    good.sort(key=lambda o: (o["p"], o["chain"], o["from"]))
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "today": today,
        "area": area,
        "towns": config["towns"],
        "chains": config["chains"],
        "products": public_products(products),
        "branches": uniq,
        "offers": good,
        "sources": status,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    STATUS.write_text(json.dumps({"updated": out["updated"], "sources": status, "log": log_lines},
                                 ensure_ascii=False, indent=1), encoding="utf-8")

    summary = (f"Hotovo: {len(good)} akcí na stránce, {len(review)} ke kontrole, "
               f"{len(uniq)} prodejen.")
    log(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("### Denní stahování akcí\n\n" + "\n".join(f"- {line}" for line in log_lines) + "\n")
    return out, review, status


if __name__ == "__main__":
    _, _, st = run()
    sys.exit(0 if any(s["ok"] for s in st.values()) else 1)
