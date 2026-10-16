"""Check San Diego Humane Society Dog Day Out (Waitwhile) for open slots and push a phone alert via ntfy."""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BASE = os.environ.get("API_BASE", "https://api.waitwhile.com/v2/public/visits/dogdayoutsandiego")
TOPIC = os.environ.get("NTFY_TOPIC", "")
BOOK_URL = "https://waitwhile.com/locations/dogdayoutsandiego/time"
STATE = "state.json"
DAYS_AHEAD = 30

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dogday-alerts/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    la = ZoneInfo("America/Los_Angeles")
    now = datetime.now(la)
    end = now + timedelta(days=DAYS_AHEAD)
    fmt = "%Y-%m-%dT%H:%M"
    q = urllib.parse.urlencode({"fromDate": now.strftime(fmt), "toDate": end.strftime(fmt), "maxNumSlots": 50})
    slots = get(f"{BASE}/first-available-slots?{q}")
    # Each slot is expected to be a date string or an object with a date; keep it flexible.
    names = sorted({(s if isinstance(s, str) else s.get("date", json.dumps(s, sort_keys=True))) for s in slots})
    print(f"{now:%Y-%m-%d %H:%M} open slots: {names or 'none'}")

    try:
        prev = json.load(open(STATE))
    except Exception:
        prev = []
    new = [n for n in names if n not in prev]
    if new and TOPIC:
        def nice(n):
            try:
                return datetime.fromisoformat(n).strftime("%a %b %-d %-I:%M%p")
            except Exception:
                return n
        pretty = ", ".join(nice(n) for n in new[:6])
        body = f"Dog Day Out opening: {pretty}" + (f" (+{len(new)-6} more)" if len(new) > 6 else "")
        req = urllib.request.Request(
            f"https://ntfy.sh/{TOPIC}", data=body.encode(),
            headers={"Title": "Dog Day Out spot open!", "Priority": "high", "Tags": "dog", "Click": BOOK_URL})
        urllib.request.urlopen(req, timeout=30).read()
        print("notified:", body)
    elif new:
        print("NTFY_TOPIC not set; would have notified:", new)
    json.dump(names, open(STATE, "w"))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("check failed:", repr(e)); sys.exit(1)
