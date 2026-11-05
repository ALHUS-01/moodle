#!/usr/bin/env python3
"""يجلب تقويم مودل (iCal) ويحوّله إلى data.json للداشبورد.

الرابط يؤخذ من متغير البيئة MOODLE_ICS_URL (يُخزَّن كـ GitHub Secret).
لا يحتاج أي مكتبات خارجية.

قواعد الاختيار (نفس منطق الداشبورد الأصلي):
  - الكويز/الامتحان: يظهر موعد "يُفتح" (opens) إذا لم يبدأ بعد، وإلا موعد الإغلاق.
  - المهمة: يظهر موعد التسليم/الإغلاق (مستحق / يُغلق / due / closes)، ويُتجاهل "يُفتح".
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

URL = os.environ.get("MOODLE_ICS_URL")
if not URL:
    sys.exit("MOODLE_ICS_URL is not set")

EXAM_WORDS = re.compile(r"quiz|exam|midterm|final|test|كويز|اختبار|امتحان|نصفي|نهائي", re.I)

# الكلمات التي يضيفها مودل للعنوان (إنجليزي/عربي، مع التشكيل أو بدونه)
OPEN_LABELS = r"opens?|يُ?فتح"
CLOSE_LABELS = r"closes?|is due|due|يُ?غلق|مستحق"
OPEN_EDGE = re.compile(rf"^\s*(?:{OPEN_LABELS})\s+|\s+(?:{OPEN_LABELS})\s*$", re.I)
CLOSE_EDGE = re.compile(rf"^\s*(?:{CLOSE_LABELS})\s+|\s+(?:{CLOSE_LABELS})\s*$", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "moodle-dashboard-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def unescape(v):
    return v.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def parse_dt(v, tzid=None):
    v = v.strip()
    if v.endswith("Z"):
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if "T" in v:
        dt = datetime.strptime(v, "%Y%m%dT%H%M%S")
        if tzid and ZoneInfo:
            try:
                return dt.replace(tzinfo=ZoneInfo(tzid)).astimezone(timezone.utc)
            except Exception:
                pass
        return dt.replace(tzinfo=timezone.utc)
    return datetime.strptime(v, "%Y%m%d").replace(tzinfo=timezone.utc)


def parse_events(ics):
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfold(ics), re.S):
        props = {}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            name, *params = key.split(";")
            name = name.upper()
            props[name] = unescape(val)
            for p in params:
                if p.upper().startswith("TZID="):
                    props[name + "_TZID"] = p.split("=", 1)[1]
        yield props


def split_title(title):
    """يرجع (العنوان بدون كلمة يُفتح/يُغلق/مستحق، نوع الحدث: open/close/other)."""
    t = title.strip()
    kind = "other"
    if OPEN_EDGE.search(t):
        kind = "open"
    elif CLOSE_EDGE.search(t):
        kind = "close"
    base = CLOSE_EDGE.sub("", OPEN_EDGE.sub("", t)).strip() or t
    return base, kind


def main():
    now = datetime.now(timezone.utc)
    groups = {}
    total = 0
    for ev in parse_events(fetch(URL)):
        if "DTSTART" not in ev or not ev.get("SUMMARY", "").strip():
            continue
        total += 1
        when = parse_dt(ev["DTSTART"], ev.get("DTSTART_TZID"))
        base, kind = split_title(ev["SUMMARY"])
        course = ev.get("CATEGORIES", "").strip() or "—"
        m = re.search(r"https?://\S+", ev.get("DESCRIPTION", ""))
        g = groups.setdefault((course, base), {"open": [], "close": [], "other": [], "url": ""})
        g[kind].append(when)
        g["url"] = g["url"] or ev.get("URL") or (m.group(0) if m else "")

    items = []
    for (course, base), g in groups.items():
        opens, closes, others = (sorted(x for x in g[k] if x > now) for k in ("open", "close", "other"))
        is_exam = bool(EXAM_WORDS.search(base))
        pick = (opens or closes or others) if is_exam else (closes or others)
        if not pick:
            if opens or closes or others:
                print(f"skipped (no usable date): {base}")
            continue
        items.append({
            "id": f"{course}|{base}",
            "type": "exam" if is_exam else "assignment",
            "course": course,
            "title": base,
            "due": pick[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": g["url"],
        })

    items.sort(key=lambda i: i["due"])
    for i in items:
        print(f"  [{i['type']:10}] {i['due']}  {i['title']}")
    out = {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Read {total} calendar events -> wrote {len(items)} items")


if __name__ == "__main__":
    main()
