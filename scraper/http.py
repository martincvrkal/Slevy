"""Jednoduché stahování s opakováním a slušným tempem."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (compatible; SlevyNachodsko/0.1; "
    "+https://github.com/Martincvrkal/slevy)"
)
PAUSE_S = 1.0  # pauza mezi dotazy na stejný web
_last_call = {}


def _pause(host):
    last = _last_call.get(host, 0)
    wait = PAUSE_S - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.time()


def get(url, headers=None, tries=3, timeout=40):
    host = urllib.parse.urlparse(url).netloc
    req_headers = {"User-Agent": USER_AGENT, "Accept-Language": "cs-CZ,cs;q=0.9"}
    if headers:
        req_headers.update(headers)
    error = None
    for attempt in range(tries):
        _pause(host)
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as e:
            error = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Nepodařilo se stáhnout {url}: {error}")


def get_json(url, headers=None):
    return json.loads(get(url, headers={"Accept": "application/json", **(headers or {})}))


def post_json(url, payload, headers=None, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
