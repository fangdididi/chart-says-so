#!/usr/bin/env python3
"""chart-says-so: check that the words on a chart are earned by its numbers.

Reads a chart card (JSON), tests every claim found in the title, subtitle,
annotations and alt text against the series data, lints the chart's words and
scaffolding, and prints a gate: SHIP, FIX or HOLD.

Usage:
  python3 chartcheck.py card.json            # markdown report
  python3 chartcheck.py card.json --json     # machine-readable result
  python3 chartcheck.py --blank > card.json  # starter card
Exit code: 0 SHIP, 1 FIX, 2 HOLD, 3 bad input.
"""
import json, re, sys

BLANK = {
    "kind": "line",
    "title": "",
    "subtitle": "",
    "y": {"label": "", "unit": "", "min": None, "log": False},
    "x": {"label": ""},
    "series": [{"name": "", "points": [["2020", 0], ["2021", 0]]}],
    "labels": "direct",
    "value_labels": "none",
    "gridlines": "light",
    "second_axis": False,
    "decoration": [],
    "annotations": [],
    "source": "",
    "alt": "",
}

UP = r"(?:rose|rise|rises|grew|grow|grows|increased|increase|increases|climbed|climbs|jumped|jumps|gained|gains|up|surged|surges|soared|上涨|增长|上升|提高|增加|攀升|涨了|多了)"
DOWN = r"(?:fell|falls|fall|dropped|drops|declined|declines|decreased|decreases|down|slid|slides|shrank|shrinks|sank|plunged|下降|下跌|减少|回落|降低|跌了|少了)"
NUM = r"(\d+(?:\.\d+)?)"
PCT_UNIT = r"(percentage points?|个百分点|pp|points?|percent|per cent|%|％)"

MULT_WORDS = [
    (r"\bquadrupled\b|翻两番", 4.0), (r"\btripled\b|翻了?三倍|增长了?两倍", 3.0),
    (r"\bdoubled\b|翻倍|翻了一番|翻番", 2.0), (r"\bhalved\b|减半|腰斩", 0.5),
]
TOP_WORDS = r"(record high|all-time high|highest|new high|peak|历史新高|创新高|新高|最高|创纪录)"
LOW_WORDS = r"(record low|all-time low|lowest|new low|历史新低|新低|最低)"

TYPE_WORDS = r"(line chart|bar chart|column chart|pie chart|area chart|scatter ?plot|donut chart|chart of|graph of|plot of|visuali[sz]ation of|折线图|柱状图|条形图|饼图|面积图|散点图|图表)"
READING = r"(hover|tap a|click (?:the )?legend|each (?:point|dot|bar|line) (?:represents|shows|is)|the (?:x|y)[- ]axis shows|this chart shows|below shows|悬停|点击图例|每个点代表|每根柱子代表|横轴表示|纵轴表示|本图展示|下图显示)"
VERB_HINT = UP + "|" + DOWN + r"|(?:is|are|was|were|has|have|had|hit|beat|overtook|passed|leads|lags|stayed|held|flat|than|超过|领先|落后|持平|保持|是|成为|仍)"
TREND_WORDS = r"(surg|soar|plung|crash|skyrocket|飙升|暴跌|狂涨|崩)"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pts(series):
    out = []
    for p in series.get("points", []):
        if isinstance(p, (list, tuple)) and len(p) == 2 and num(p[1]) is not None:
            out.append((str(p[0]), float(p[1])))
    return out


def window(text, points):
    """Cut the points to a year window named in the claim text, if any."""
    m = re.search(r"(?:from|between)\s+(\d{4})\s+(?:to|and)\s+(\d{4})", text) or \
        re.search(r"(\d{4})\s*(?:-|–|—|到|至)\s*(\d{4})", text)
    if m:
        a, b = m.group(1), m.group(2)
        ia = next((i for i, p in enumerate(points) if p[0].startswith(a)), None)
        ib = next((i for i, p in enumerate(points) if p[0].startswith(b)), None)
        if ia is None or ib is None:
            return None, "window %s-%s not in data" % (a, b)
        return points[ia:ib + 1], "%s→%s" % (points[ia][0], points[ib][0])
    m = re.search(r"since\s+(\d{4})|(\d{4})\s*年以来|自\s*(\d{4})", text)
    if m:
        a = next(g for g in m.groups() if g)
        ia = next((i for i, p in enumerate(points) if p[0].startswith(a)), None)
        if ia is None:
            return None, "start %s not in data" % a
        return points[ia:], "%s→%s" % (points[ia][0], points[-1][0])
    if not points:
        return None, "no data"
    return points, "%s→%s" % (points[0][0], points[-1][0])


def pick_series(text, card):
    ss = card.get("series", [])
    if len(ss) == 1:
        return ss[0]
    hits = [s for s in ss if s.get("name") and s["name"].lower() in text.lower()]
    return hits[0] if len(hits) == 1 else None


def close(actual, claimed, rel=0.05, absol=0.5):
    return abs(actual - claimed) <= max(absol, abs(claimed) * rel)


def check_sentence(text, where, card):
    """Return a list of claim results for one sentence."""
    res = []
    y_is_pct = (card.get("y", {}) or {}).get("unit", "").strip() in ("%", "％", "percent", "pct")
    s = pick_series(text, card)

    def base(kind, said):
        return {"where": where, "text": text.strip(), "kind": kind, "said": said}

    found = []
    for m in re.finditer(UP + r"\s*(?:by\s+|了\s*)?(?:about\s+|nearly\s+|almost\s+|约\s*|近\s*)?" + NUM + r"\s*" + PCT_UNIT, text, re.I):
        found.append(("change", +1, float(m.group(1)), m.group(2), m.group(0)))
    for m in re.finditer(DOWN + r"\s*(?:by\s+|了\s*)?(?:about\s+|nearly\s+|almost\s+|约\s*|近\s*)?" + NUM + r"\s*" + PCT_UNIT, text, re.I):
        found.append(("change", -1, float(m.group(1)), m.group(2), m.group(0)))
    for pat, f in MULT_WORDS:
        m = re.search(pat, text, re.I)
        if m:
            found.append(("ratio", 1 if f > 1 else -1, f, "x", m.group(0)))
    m = re.search(NUM + r"\s*(?:x|×|times|倍)\b", text, re.I) if not any(k == "ratio" for k, *_ in found) else None
    if m and re.search(r"(more|larger|bigger|higher|grew|than|增长|是)", text, re.I):
        found.append(("ratio", 1, float(m.group(1)), "x", m.group(0)))
    if re.search(TOP_WORDS, text, re.I):
        found.append(("extreme", +1, None, "", re.search(TOP_WORDS, text, re.I).group(0)))
    if re.search(LOW_WORDS, text, re.I):
        found.append(("extreme", -1, None, "", re.search(LOW_WORDS, text, re.I).group(0)))
    if not found:
        bare_up = re.search(r"(?<![a-z])" + UP + r"(?![a-z])", text, re.I)
        bare_dn = re.search(r"(?<![a-z])" + DOWN + r"(?![a-z])", text, re.I)
        if bare_up and not bare_dn:
            found.append(("direction", +1, None, "", bare_up.group(0)))
        elif bare_dn and not bare_up:
            found.append(("direction", -1, None, "", bare_dn.group(0)))

    for kind, sign, val, unit, said in found:
        r = base(kind, said)
        if s is None:
            r.update(verdict="UNCHECKED", why="cannot tell which series the claim is about; name it")
            res.append(r); continue
        p = pts(s)
        w, span = window(text, p)
        if not w or len(w) < 2:
            r.update(verdict="UNCHECKED", why=span if w is None else "fewer than two points in window")
            res.append(r); continue
        a, b = w[0][1], w[-1][1]
        r["series"] = s.get("name", "")
        r["window"] = span
        if kind == "change":
            pp = b - a
            rel = (b - a) / abs(a) * 100 if a else None
            is_points = re.search(r"point|pp|个百分点", unit, re.I) is not None
            if is_points:
                actual, label = pp, "points"
            elif y_is_pct:
                # "%" on a percent axis is ambiguous; accept whichever reading matches, flag it
                if rel is not None and close(abs(rel), val) and (rel > 0) == (sign > 0):
                    actual, label = rel, "% relative"
                else:
                    actual, label = pp, "points (read as)"
                r["ambiguous_pct"] = True
            else:
                if rel is None:
                    r.update(verdict="UNCHECKED", why="start value is zero; a % change is undefined")
                    res.append(r); continue
                actual, label = rel, "% relative"
            r["actual"] = "%+.1f %s" % (actual, label)
            if actual == 0 or (actual > 0) != (sign > 0):
                r["verdict"] = "WRONG"; r["why"] = "data moves the other way (or not at all)"
            elif close(abs(actual), val):
                r["verdict"] = "HOLDS"
            else:
                r["verdict"] = "STRETCH"; r["why"] = "direction right, size off: said %g, data %.1f" % (val, abs(actual))
        elif kind == "ratio":
            if a == 0:
                r.update(verdict="UNCHECKED", why="start value is zero; a multiple is undefined"); res.append(r); continue
            ratio = b / a
            r["actual"] = "×%.2f" % ratio
            if (ratio > 1) != (val > 1) or ratio == 1:
                r["verdict"] = "WRONG"; r["why"] = "data moves the other way"
            elif abs(ratio - val) <= 0.1 * val:
                r["verdict"] = "HOLDS"
            else:
                r["verdict"] = "STRETCH"; r["why"] = "said ×%g, data ×%.2f" % (val, ratio)
        elif kind == "extreme":
            vals = [v for _, v in p]
            target = max(vals) if sign > 0 else min(vals)
            last = w[-1][1]
            r["actual"] = "last %g, %s %g" % (last, "max" if sign > 0 else "min", target)
            if last == target:
                r["verdict"] = "HOLDS"
                if re.search(r"record|all-time|历史|创纪录", said, re.I) and len(p) < 10:
                    r["verdict"] = "STRETCH"; r["why"] = "'record' over only %d points; say 'highest since %s'" % (len(p), p[0][0])
            else:
                r["verdict"] = "WRONG"; r["why"] = "the latest point is not the %s in the data shown" % ("highest" if sign > 0 else "lowest")
        else:  # direction only
            r["actual"] = "%g → %g" % (a, b)
            if b == a or (b > a) != (sign > 0):
                r["verdict"] = "WRONG"; r["why"] = "data moves the other way (or not at all)"
            else:
                r["verdict"] = "HOLDS"
        # cherry-picked start: claim of growth starting exactly at the series low
        if kind in ("change", "ratio", "direction") and r.get("verdict") in ("HOLDS", "STRETCH") and len(p) >= 4:
            vals = [v for _, v in p]
            if sign > 0 and a == min(vals) and w[0] != p[0]:
                r["start_at_low"] = True
            if sign < 0 and a == max(vals) and w[0] != p[0]:
                r["start_at_high"] = True
        res.append(r)
    return res


def sentences(card):
    out = []
    for key in ("title", "subtitle", "alt"):
        t = card.get(key) or ""
        for part in re.split(r"(?<=[.!?。！？;；])\s*", t):
            if part.strip():
                out.append((key, part))
    for i, a in enumerate(card.get("annotations", []) or []):
        t = a.get("text", "") if isinstance(a, dict) else str(a)
        if t.strip():
            out.append(("annotation %d" % (i + 1), t))
    return out


def lint(card, claims):
    f = []
    kind = (card.get("kind") or "").lower()
    title = card.get("title") or ""
    y = card.get("y") or {}
    series = card.get("series") or []
    words = " ".join([title, card.get("subtitle") or "", card.get("alt") or ""] +
                     [(a.get("text", "") if isinstance(a, dict) else str(a)) for a in card.get("annotations", []) or []])

    def add(code, level, msg):
        f.append({"code": code, "level": level, "msg": msg})

    if not title.strip():
        add("C01 NO-TITLE", "fix", "no title; write the one thing a reader should take away")
    elif re.search(TYPE_WORDS, title, re.I):
        add("C02 NAMES-THE-CHART", "fix", "title names the chart type or topic; replace with the takeaway in a sentence")
    elif not re.search(VERB_HINT, title, re.I) and not re.search(r"\d", title):
        add("C03 TOPIC-TITLE", "warn", "title is a topic, not a finding; state what the data says (keep the topic for the subtitle)")
    if re.search(READING, words, re.I):
        add("C04 READING-INSTRUCTIONS", "fix", "text tells the reader how to read the chart; let labels do it or cut it")
    if card.get("subtitle") and title and card["subtitle"].strip().lower() == title.strip().lower():
        add("C05 SAID-TWICE", "fix", "subtitle repeats the title")
    if (card.get("value_labels") == "all") and (card.get("gridlines") in ("light", "dense")):
        add("C05 SAID-TWICE", "warn", "a value on every mark plus gridlines; keep one (label the few points that matter)")
    if card.get("gridlines") == "dense":
        add("C06 HEAVY-SCAFFOLD", "warn", "dense gridlines; use a few light ones or none")
    deco = [d for d in (card.get("decoration") or []) if d]
    if deco:
        lvl = "fix" if any(d in ("3d", "3D") for d in deco) else "warn"
        add("C06 HEAVY-SCAFFOLD", lvl, "decoration with no data job: %s" % ", ".join(deco))
    if card.get("labels") == "legend" and kind in ("line", "area", "slope") and 2 <= len(series) <= 6:
        add("C07 LEGEND-NOT-LABEL", "warn", "%d lines with a legend; put each name at its line end" % len(series))
    if not (y.get("unit") or "").strip() and kind != "pie":
        add("C08 NO-UNIT", "fix", "value axis has no unit (%, ¥, people, ms...); say what is counted")
    if not (card.get("source") or "").strip():
        add("C09 NO-SOURCE", "fix", "no source line; name where the numbers come from and their date")
    ymin = num(y.get("min"))
    if kind in ("bar", "column", "area", "stacked") and ymin is not None and ymin > 0 and not y.get("log"):
        add("C10 CUT-BASELINE", "hold", "%s chart with value axis starting at %g; bar length must start at zero" % (kind, ymin))
    if card.get("second_axis"):
        add("C11 TWIN-AXES", "fix", "two value axes invite a fake correlation; split into two panels or index both to 100")
    if kind in ("pie", "donut"):
        vals = [v for s in series for _, v in pts(s)]
        if len(vals) > 5:
            add("C12 PIE-CROWD", "fix", "%d slices; keep 5 or fewer or switch to sorted bars" % len(vals))
        tot = sum(vals)
        if vals and (card.get("share", True)) and not (95 <= tot <= 105) and (y.get("unit") in ("%", "％")):
            add("C12 PIE-CROWD", "hold", "slices sum to %g%%, not 100%%" % tot)
    if any(c.get("ambiguous_pct") for c in claims):
        add("C13 PERCENT-VS-POINTS", "fix", "a % change on a % axis; write 'points' for the difference or 'relative' for the ratio")
    for c in claims:
        if c.get("start_at_low") or c.get("start_at_high"):
            add("C14 CHOSEN-START", "warn", "'%s' starts at the series %s (%s); show or mention the earlier points" %
                (c["said"], "low" if c.get("start_at_low") else "high", c.get("window", "")))
    n = max((len(pts(s)) for s in series), default=0)
    if re.search(TREND_WORDS, words, re.I) and n <= 3:
        add("C15 THIN-TREND", "fix", "trend language on %d points; say 'X vs Y' instead of a trend" % n)
    alt = (card.get("alt") or "").strip()
    if not alt:
        add("C16 NO-ALT", "fix", "no alt text; write the takeaway plus the range of the data in one or two sentences")
    elif re.search(TYPE_WORDS, alt, re.I) and not re.search(r"\d", alt):
        add("C16 NO-ALT", "fix", "alt text names the chart but gives no finding or numbers")
    if re.search(r"(?<![\w.])(blazing|game-?changing|unprecedented|stunning|incredible|惊人|震撼|史无前例)", words, re.I):
        add("C17 HYPE-WORD", "warn", "hype word on a chart; let the number carry it")
    return f


def gate(claims, finds):
    if any(c["verdict"] == "WRONG" for c in claims) or any(x["level"] == "hold" for x in finds):
        return "HOLD"
    if any(c["verdict"] in ("STRETCH", "UNCHECKED") for c in claims) or any(x["level"] == "fix" for x in finds):
        return "FIX"
    return "SHIP"


def run(card):
    claims = []
    for where, text in sentences(card):
        claims += check_sentence(text, where, card)
    finds = lint(card, claims)
    return {"gate": gate(claims, finds), "claims": claims, "findings": finds}


def report(card, r):
    L = ["# chart-says-so report", "", "**Gate: %s**" % r["gate"], "",
         "Title: %s" % (card.get("title") or "(none)"), ""]
    L.append("## Claims (%d)" % len(r["claims"]))
    if not r["claims"]:
        L.append("No checkable claim found. If the title states a finding, rephrase it with a number, a direction or a year window, or check it by hand.")
    else:
        L += ["", "| # | Where | Said | Series | Window | Data | Verdict | Why |", "|---|---|---|---|---|---|---|---|"]
        for i, c in enumerate(r["claims"], 1):
            L.append("| %d | %s | %s | %s | %s | %s | %s | %s |" % (
                i, c["where"], c["said"], c.get("series", ""), c.get("window", ""),
                c.get("actual", ""), c["verdict"], c.get("why", "")))
    L += ["", "## Findings (%d)" % len(r["findings"])]
    if not r["findings"]:
        L.append("None.")
    for x in r["findings"]:
        L.append("- [%s] %s: %s" % (x["level"].upper(), x["code"], x["msg"]))
    L += ["", "SHIP = every claim holds and nothing to fix. FIX = rewrite before publishing. HOLD = the chart says something false or draws a lie; do not publish."]
    return "\n".join(L)


def main(argv):
    if "--blank" in argv:
        print(json.dumps(BLANK, indent=2, ensure_ascii=False)); return 0
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__); return 3
    try:
        with open(paths[0], encoding="utf-8") as fh:
            card = json.load(fh)
    except Exception as e:
        print("cannot read card: %s" % e); return 3
    r = run(card)
    if "--json" in argv:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(report(card, r))
    return {"SHIP": 0, "FIX": 1, "HOLD": 2}[r["gate"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
