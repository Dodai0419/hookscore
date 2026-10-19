# AGENTS.md: hookscore

Use when the user wants a hook (the first line of a Reel, Short or YouTube video) scored, ranked against alternatives, or checked before recording.

## How to use
1. Put candidate hooks in a text file, one per line (or use `--hook "..."` for one).
2. Run, from the repo root:
   - Reels / short-form: `python hookscore.py hooks.txt`
   - YouTube long-form: `python hookscore.py --for youtube hooks.txt`
   - Add `--json` for machine-readable output.
3. Read the weakest property and its fix, rewrite that part, re-run.

## Rules
- Write 3+ candidate hooks and rank them; do not score a single draft and stop.
- Reel scores of 70+ with no dealbreakers are `STRONG`. YouTube: 72+ `STRONG`, 55+ `WORKABLE`.
- Treat a high score as "nothing obviously wrong", never as a view prediction.
- Reel exit code is 1 when no hook reaches 70, so it can gate a script.
