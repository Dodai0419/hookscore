<div align="center">

# hookscore

**Score the first line of a Reel or a YouTube video before you waste a take on it.**

One file that merges the two hook scorers from Jake Schincariol's Instagram and YouTube agent skills, score-for-score identical, and names the hook formula for both.

Works with **Claude Code** and **Codex**.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Status: prototype](https://img.shields.io/badge/status-prototype-orange.svg)

</div>

## Quick start
```bash
git clone https://github.com/Dodai0419/hookscore && cd hookscore
python hookscore.py --hook "Stop paying for software you open twice a year."
```
```
  LENGTH        ######################## 100.0
  SPECIFICITY   ##################......  75.0
  STAKES        #################.......  70.0
  FRONTLOAD     ######################## 100.0
  ADDRESS       ######################## 100.0
  HOOK SCORE    ####################....  81.4   STRONG
  formula       Negative Command
```
Rank a batch, or score for YouTube instead:
```bash
python hookscore.py examples/hooks.txt
python hookscore.py --for youtube examples/hooks.txt --json
```

## The problem
- The Reel scorer and the YouTube scorer live in two repos, with two different CLIs and two JSON shapes.
- The Reel scorer never tells you which of its 26 formulas a hook uses; that only happens in a separate swipe-file script.
- The YouTube scorer opens files with the system code page, so a single curly apostrophe crashes it on Windows (`UnicodeDecodeError: 'cp949' codec ...`).

## The solution
| Idea | Fixes |
|------|-------|
| **One CLI, `--for reel` or `--for youtube`** | Two tools and two install steps become one file with no dependencies |
| **Formula naming for Reels too** | Each Reel hook gets its formula name (first match in the original `classify_order`) |
| **UTF-8 in and out** | Curly quotes, em dashes and emoji no longer crash on Windows consoles |
| **Same numbers as the originals** | 83 hooks are checked against recorded upstream output in the tests |

What it measures: Reel = LENGTH, SPECIFICITY, STAKES, FRONTLOAD, ADDRESS plus dealbreakers (greetings, "in this video", hashtags, emoji). YouTube = SPECIFICITY, ADDRESS, STAKES, CURIOSITY, BREVITY. Both weight the weakest property at 40%.
What it does not do: predict views. The upstream author reports AUC 0.83 for real hooks vs deliberately bad ones, and 0.56 for a creator's hits vs their misses. A low score is a reason to look again, not a high score a promise.

## Use with Claude Code
```bash
/plugin marketplace add Dodai0419/hookscore
/plugin install hookscore@hookscore
```

## Use with Codex (ChatGPT)
```bash
git clone https://github.com/Dodai0419/hookscore && cp -r hookscore/skills/* ~/.codex/skills/
```
Or copy `AGENTS.md` into your project root.

## Benchmarks
| | original (2 repos) | this repo |
|-|-|-|
| lines of code (scorer scripts) | 313 + 129 = 442 | 278 |
| dependencies | 0 | 0 |
| Reel, 1,022 hooks, `--json` (median wall) | 612 / 709 ms | 542 / 597 ms (also names formulas) |
| YouTube, 1,022 hooks, `--json` (median wall) | 681 / 690 ms | 549 / 619 ms |
| Reel, single hook (median wall) | 306 / 351 ms | 244 / 285 ms |
| non-ASCII hook file on a cp949 console | YouTube scorer crashes | works |

Two separate runs of 15 interleaved repetitions each (the two numbers per cell), Windows 11, Python 3.11, a busy laptop, so expect noise. Input: `tests/corpus.txt` repeated 14 times. Upstream run with `python -X utf8` so it does not crash. Speed comes from loading only the formula file the platform needs, precompiling the YouTube patterns, and dropping `argparse` and `statistics` imports.

## Inspired by
- [Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) — Reel hook checks, dealbreakers, 26 hook formulas and their classify order
- [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) — YouTube hook checks and 21 hook formulas

## Roadmap
- [ ] `--for shorts` once there is data on how Shorts hooks differ from Reels
- [ ] Score a whole transcript file and pick the first 15 seconds automatically

## License
MIT. Scoring logic and `data/*.json` are from the two upstream repos (MIT, Copyright (c) 2026 Jake Schincariol); see LICENSE.
