#!/usr/bin/env python3
"""hookscore - score the first line of a Reel or a YouTube video, rank a batch, name its formula.

Two scorers in one file, each kept score-for-score identical to the original:
  --for reel     5 checks from instagram-agent-skill (LENGTH SPECIFICITY STAKES FRONTLOAD ADDRESS)
  --for youtube  5 checks from youtube-agent-skill (SPECIFICITY ADDRESS STAKES CURIOSITY BREVITY)

It catches greetings, preambles, vague lines and hooks too long to say. It does not predict views.

  python hookscore.py examples/hooks.txt               # one hook per line, ranked
  python hookscore.py --for youtube --hook "one line"
  python hookscore.py --json examples/hooks.txt
"""
import functools, json, os, re, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@functools.lru_cache(None)  # each platform loads only its own formula file, once
def formulas(platform):
    with open(os.path.join(DATA, platform + "-hooks.json"), encoding="utf-8") as f:
        d = json.load(f)
    if platform == "youtube":
        return [(h["name"], [re.compile(p, re.I) for p in h["match"]]) for h in d["hooks"]]
    by_id = {h["id"]: h for h in d["hooks"]}
    return [(by_id[i]["name"], re.compile(by_id[i]["match"], re.I))
            for i in d.get("classify_order") or sorted(by_id) if i in by_id]


def clamp(n, lo=0.0, hi=100.0):
    return max(lo, min(hi, n))


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


# ---------------------------------------------------------------- reel (Instagram)
WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")
NUMBER_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b"
    r"|days?\b|weeks?\b|months?\b|years?\b)?", re.IGNORECASE)
PROPER_RE = re.compile(r"(?<!^)\b[A-Z][a-z]{2,}\b")
# "one" and "first" are absent on purpose: they are filler far more often than a quantity.
SPOKEN_NUMBERS = set("zero two three four five six seven eight nine ten eleven twelve fifteen twenty "
                     "thirty forty fifty sixty seventy eighty ninety hundred thousand million billion "
                     "dozen half twice triple".split())
MONEY_WORDS = set("dollars dollar bucks grand percent cents millionaire billionaire revenue profit "
                  "salary rent".split())
STAKES = set("stop never wrong mistake mistakes lost lose losing cost costs broke broken failed failure "
             "fail nobody no not don't dont doesn't didn't can't won't quit quitting fired deleted delete "
             "killed kills kill replaced replaces cut beat free paid charged hired saved first banned "
             "illegal worst hate hated wasted waste scam lie lied lying truth secret hidden stole stolen "
             "before until instead but except unless problem risk danger warning regret wish should "
             "shouldn't still already only without versus vs actually".split())
WEAK_OPENERS = ["so", "ok", "okay", "hey", "hi", "hello", "guys", "yo", "alright", "welcome", "today",
                "basically", "honestly", "look", "listen", "um", "just", "let", "lets", "let's",
                "i wanted", "i want", "one of", "have you", "did you", "do you", "are you", "in this",
                "in today", "the thing", "a lot", "there is", "there are", "this is", "it is", "as a",
                "when it", "if you've", "you know"]
IMPERATIVES = set("stop steal copy delete try watch read save use build make write send take start quit "
                  "never always don't dont do put run check".split())
DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:stop scrolling|don'?t scroll)"),
     "Opens with \"stop scrolling\". Asking for attention proves you have not earned it."),
    (re.compile(r"(?i)\b(?:in (?:this|today'?s) (?:video|reel)|i'?m going to show you|i'?ll show you how)\b"),
     "Video preamble. Delete it and open on the payoff."),
    (re.compile(r"(?i)^\s*(?:hey |hi |what'?s up |welcome )"),
     "Greeting. Nobody came to the feed to be greeted."),
    (re.compile(r"(?:^|\s)#\w+"),
     "Hashtag in the hook. Hashtags belong at the bottom of the caption, if anywhere."),
    (re.compile(r"[\U0001F300-\U0001FAFF☀-➿]"),
     "Emoji in the hook. On-screen text at hook size has room for words or for an emoji, not both."),
]
REEL_CHECKS = ["LENGTH", "SPECIFICITY", "STAKES", "FRONTLOAD", "ADDRESS"]
WEAK_START, WEAK_SET = tuple(WEAK_OPENERS), set(WEAK_OPENERS)


def ig_words(text):
    # "$18,000" is one spoken word, so it is one word here too.
    return WORD_RE.findall(re.sub(r"(?<=\d),(?=\d)", "", text))


def check_length(text, w, low):
    n, chars = len(w), len(text.strip())
    score = 100.0 if 5 <= n <= 12 else clamp(100 - (5 - n) * 20) if n < 5 else clamp(100 - (n - 12) * 11)
    if chars > 60:  # two lines of big on-screen text
        score -= 12
    return clamp(score), f"{n} words, {chars} chars, ~{n / 2.75:.1f}s spoken (want 5-12 words)"


def check_specificity(text, w, low):
    nums = [n.strip() for n in NUMBER_RE.findall(text) if n.strip()]
    propers = set(PROPER_RE.findall(text))
    spoken = [x for x in low if x in SPOKEN_NUMBERS or x in MONEY_WORDS]
    hits = len(nums) + len(propers) + len(spoken)
    found = ", ".join(nums[:2] + sorted(propers)[:2] + spoken[:2])
    return (15.0 if hits == 0 else clamp(45 + hits * 30),
            f"{hits} concrete marker(s)" + (f": {found}" if found else " - no number, no name, nothing checkable"))


def check_stakes(text, w, low):
    markers = sorted({x for x in low if x in STAKES})
    if re.search(r"\$\s?\d", text):
        markers.append("a price")
    n = len(markers)
    return clamp({0: 20.0, 1: 70.0}.get(n, 100.0)), f"{n} tension marker(s)" + (
        f": {', '.join(markers[:4])}" if markers else " - nothing is at stake in this line")


def check_frontload(text, w, low):
    if not w:
        return 0.0, "empty"
    opener, penalty, hit = " ".join(low[:2]), 0, None
    if opener.startswith(WEAK_START) or low[0] in WEAK_SET:  # fast path; the loop keeps the original's pick
        hit = next(weak for weak in WEAK_OPENERS if opener.startswith(weak) or low[0] == weak)
        penalty = 30
    payload = next((i for i, t in enumerate(low) if t in STAKES or t in SPOKEN_NUMBERS or t in MONEY_WORDS
                    or NUMBER_RE.match(w[i]) or (i and PROPER_RE.match(w[i]))), None)
    if payload is None:
        base, where = 30.0, "no payload word anywhere in the line"
    elif payload <= 3:
        base, where = 100.0, f"payload at word {payload + 1}"
    elif payload <= 6:
        base, where = 70.0, f"payload at word {payload + 1}, could move forward"
    else:
        base, where = 40.0, f"payload at word {payload + 1}, too late"
    return clamp(base - penalty), where + (f"; weak opener \"{hit}\"" if hit else "")


def check_address(text, w, low):
    lower = text.lower()
    if re.search(r"\b(you|your|you're|youre|yourself)\b", lower):
        return 100.0, "speaks to the viewer"
    if low and low[0] in IMPERATIVES:
        return 90.0, f"imperative opener (\"{low[0]}\")"
    if re.search(r"\b(i|my|me|we|our)\b", lower):
        return 70.0, "first person, no viewer named"
    return 35.0, "third person, nobody in the room"


def score_reel(text):
    w = ig_words(text)
    low = [x.lower().strip("'’") for x in w]
    res = dict(zip(REEL_CHECKS, (f(text, w, low) for f in
                                 (check_length, check_specificity, check_stakes, check_frontload, check_address))))
    flags = [msg for pat, msg in DEALBREAKERS if pat.search(text)]
    scores = [res[c][0] for c in REEL_CHECKS]
    # The weakest property caps the hook: one bad property is enough for the thumb to keep moving.
    overall = clamp(sum(scores) / 5 * 0.6 + min(scores) * 0.4 - len(flags) * 15)
    verdict = "STRONG" if overall >= 70 and min(scores) >= 55 and not flags else "OK" if overall >= 50 else "WEAK"
    return {"hook": text, "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in res.items()},
            "weakest": min(REEL_CHECKS, key=lambda c: res[c][0]), "flags": flags,
            "score": round(overall, 1), "verdict": verdict,
            "formula": next((n for n, p in formulas("reel") if p.search(text)), "unclassified")}


# ---------------------------------------------------------------- youtube
FILLER = set("basically actually literally just really very so kind sort like guys hey welcome today video "
             "subscribe channel".split())
VAGUE = set("amazing incredible insane crazy huge massive game changer secret powerful ultimate best "
            "revolutionary mind blowing unbelievable".split())
CONCRETE = re.compile(r"\b(\d[\d,.]*\s?(%|k|m|x|s|m|h)?|\$\d|\d+\s?(second|minute|hour|day|week|month|year)s?)\b", re.I)
YOU = re.compile(r"\b(you|your|you're|youre|yourself)\b", re.I)
STAKE = re.compile(r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|before|stop|never|die|dying|dead)\b", re.I)
CURIOSITY = re.compile(r"\b(why|how|what|which|until|before|but|nobody|almost|except|reason|actually)\b", re.I)
CLOSED = re.compile(r"\b(because|so that|which means)\b", re.I)
YT_FIX = {"SPECIFICITY": "swap one adjective for a number, a name or a date",
          "ADDRESS": "say 'you' in the first six words",
          "STAKES": "name what it costs them to keep doing it the current way",
          "CURIOSITY": "cut the half of the sentence that answers itself",
          "BREVITY": "9 to 24 words. Read it out loud and stop where you run out of breath"}


def score_youtube(text):
    w = re.findall(r"[a-z0-9'%$.]+", text.lower())
    n, concrete = len(w), bool(CONCRETE.search(text))
    spec = 0 if not w else int(clamp(34 + len(CONCRETE.findall(text)) * 22 - 16 * sum(x in VAGUE for x in w)
                                     - 5 * sum(x in FILLER for x in w)
                                     + min(18, 6 * sum(1 for x in text.split()[1:] if x[:1].isupper())), 0, 100))
    # 9-24 words is the band a spoken hook lands in at ~150 wpm inside 10 seconds.
    brev = 0 if n == 0 else 100 if 9 <= n <= 24 else max(30, 100 - (9 - n) * 11) if n < 9 else max(10, 100 - (n - 24) * 7)
    parts = {"SPECIFICITY": spec,
             "ADDRESS": int(clamp(26 + len(YOU.findall(text)) * 20 + (30 if YOU.search(" ".join(text.split()[:6])) else 0), 0, 100)),
             "STAKES": int(clamp(22 + len(STAKE.findall(text)) * 26 + (14 if concrete else 0), 0, 100)),
             "CURIOSITY": int(clamp(24 + len(CURIOSITY.findall(text)) * 17 + (18 if text.strip().endswith("?") else 0)
                                    - (18 if CLOSED.search(text) else 0), 0, 100)),
             "BREVITY": brev}
    vals = list(parts.values())
    verdict = round(0.6 * (sum(vals) / len(vals)) + 0.4 * min(vals))
    hits, name = max(((sum(1 for p in pats if p.search(text)), nm) for nm, pats in formulas("youtube")),
                     key=lambda h: h[0], default=(0, None))  # first formula wins a tie, like the original
    return {"hook": text.strip(), "properties": parts, "verdict": verdict,
            "band": "STRONG" if verdict >= 72 else "WORKABLE" if verdict >= 55 else "WEAK",
            "formula": name if hits else "Unclassified"}


# ---------------------------------------------------------------- output
def print_reel(rows):
    if len(rows) == 1:
        r = rows[0]
        print(f"\nHOOK SCORE\n{'=' * 62}\n  \"{r['hook'].strip()}\"\n")
        for name, c in r["checks"].items():
            print(f"  {name:<13} {bar(c['score'])} {c['score']:5.1f}\n  {'':<13} {c['detail']}")
        print(f"{'-' * 62}\n  {'HOOK SCORE':<13} {bar(r['score'])} {r['score']:5.1f}   {r['verdict']}")
        print(f"  {'formula':<13} {r['formula']}")
        for f in r["flags"]:
            print(f"\n  DEALBREAKER  {f}")
        if r["verdict"] != "STRONG":
            print(f"\n  Weakest property: {r['weakest']}. Fix that one and re-run.")
        print()
        return
    print("\nHOOK RANKING\n" + "=" * 78)
    for i, r in enumerate(sorted(rows, key=lambda r: -r["score"]), 1):
        hook = r["hook"] if len(r["hook"]) <= 62 else r["hook"][:59] + "..."
        print(f"{'->' if i == 1 else '  '} {r['score']:5.1f} {r['verdict']:<7} {hook}")
        print(f"        weakest: {r['weakest']} ({r['checks'][r['weakest']]['score']:.0f})  formula: {r['formula']}")
        for f in r["flags"]:
            print(f"        dealbreaker: {f}")
    print("\nShoot the top one. If the top one is under 50, none of these are the hook.\n")


def print_youtube(rows):
    for r in rows:
        t = r["hook"]
        print(f"\n  {t}\n  {'-' * min(72, max(20, len(t)))}")
        for k, v in r["properties"].items():
            print(f"    {k:<12} {v:3d}  {'#' * (v // 5)}")
        print(f"    {'VERDICT':<12} {r['verdict']:3d}  {r['band']}")
        print(f"    formula      {r['formula']}")
        low = min(r["properties"], key=r["properties"].get)
        print(f"    weakest      {low} - {YT_FIX[low]}")
    if len(rows) > 1:
        print(f"\n  winner: {rows[0]['hook']}  ({rows[0]['verdict']}, {rows[0]['band']})\n")


def main(argv=None):
    # Hand-rolled flags: argparse alone costs ~100 ms of startup on a slow Windows box.
    args, opts = list(sys.argv[1:] if argv is None else argv), {"--for": "reel", "--hook": None}
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    as_json = "--json" in args
    args = [x for x in args if x != "--json"]
    for flag in opts:
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                sys.exit(f"{flag} needs a value")
            opts[flag] = args.pop(i + 1)
            args.pop(i)
    platform = opts["--for"]
    if platform not in ("reel", "youtube") or len(args) > 1:
        sys.exit("usage: hookscore.py [FILE|-] [--hook TEXT] [--for reel|youtube] [--json]")
    sys.stdout.reconfigure(encoding="utf-8")  # cp949/cp1252 consoles crash on curly quotes otherwise
    if opts["--hook"]:
        lines = [opts["--hook"]]
    else:
        src = args[0] if args else "-"
        raw = sys.stdin.buffer.read().decode("utf-8") if src == "-" else open(src, encoding="utf-8").read()
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        sys.exit("nothing to score")
    if platform == "youtube":
        rows = sorted(map(score_youtube, lines), key=lambda r: -r["verdict"])
        print(json.dumps(rows, indent=1, ensure_ascii=False)) if as_json else print_youtube(rows)
        return 0
    rows = [score_reel(l) for l in lines]
    if as_json:
        print(json.dumps(rows if len(rows) > 1 else rows[0], indent=2, ensure_ascii=False))
        return 0
    print_reel(rows)
    return 0 if max(r["score"] for r in rows) >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
