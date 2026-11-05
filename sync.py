#!/usr/bin/env python3
"""يجلب تقويم مودل (iCal) ويحوّله إلى data.json للداشبورد.

الرابط يؤخذ من متغير البيئة MOODLE_ICS_URL (يُخزَّن كـ GitHub Secret).
لا يحتاج أي مكتبات خارجية.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

URL = os.environ.get("MOODLE_ICS_URL")
if not URL:
    sys.exit("MOODLE_ICS_URL is not set")

EXAM_WORDS = re.compile(r"quiz|exam|midterm|final|test|كويز|اختبار|امتحان|نصفي|نهائي", re.I)
# أحداث مودل التي تعني أن الاختبار "يُفتح" أو "يُغلق" (نريد الإغلاق = الموعد النهائي)
OPEN_WORDS = re.compile(r"opens|يُفتح|يفتح", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "moodle-dashboard-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def unescape(v):
    return v.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def parse_dt(v):
    v = v.strip()
    if v.endswith("Z"):
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if "T" in v:
        return datetime.strptime(v, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return datetime.strptime(v, "%Y%m%d").replace(tzinfo=timezone.utc)


def parse_events(ics):
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfold(ics), re.S):
        props = {}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            props[key.split(";")[0].upper()] = unescape(val)
        yield props


def main():
    now = datetime.now(timezone.utc)
    items = []
    for ev in parse_events(fetch(URL)):
        if "DTSTART" not in ev:
            continue
        due = parse_dt(ev["DTSTART"])
        if due <= now:
            continue
        title = ev.get("SUMMARY", "").strip()
        if OPEN_WORDS.search(title):
            continue
        course = ev.get("CATEGORIES", "").strip() or "—"
        desc = ev.get("DESCRIPTION", "")
        m = re.search(r"https?://\S+", desc)
        is_exam = bool(EXAM_WORDS.search(title))
        items.append({
            "id": ev.get("UID", title + due.isoformat()),
            "type": "exam" if is_exam else "assignment",
            "course": course,
            "title": title,
            "due": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": ev.get("URL") or (m.group(0) if m else ""),
        })

    items.sort(key=lambda i: i["due"])
    out = {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items")


if __name__ == "__main__":
    main()
