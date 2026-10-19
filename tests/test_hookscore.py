import json, os, subprocess, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import hookscore  # noqa: E402

HOOKS = os.path.join(ROOT, "examples", "hooks.txt")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def lines():
    with open(HOOKS, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


class ReelMatchesInstagramSkill(unittest.TestCase):
    def test_every_score_detail_and_verdict(self):
        got = [hookscore.score_reel(t) for t in lines()]
        for g, want in zip(got, load("upstream_reel.json")):
            for key in ("hook", "checks", "weakest", "flags", "score", "verdict"):
                self.assertEqual(g[key], want[key], (want["hook"], key))

    def test_formula_names_match_swipe_classifier(self):
        got = [hookscore.score_reel(t)["formula"] for t in lines()]
        self.assertEqual(got, load("upstream_reel_formulas.json"))


class YoutubeMatchesYoutubeSkill(unittest.TestCase):
    def test_ranked_output_is_identical(self):
        got = sorted((hookscore.score_youtube(t) for t in lines()), key=lambda r: -r["verdict"])
        self.assertEqual(got, load("upstream_youtube.json"))


class Corpus(unittest.TestCase):
    """73 lines: every example and on-screen line from both formula files."""

    def test_both_scorers_match_upstream_on_corpus(self):
        with open(os.path.join(HERE, "corpus.txt"), encoding="utf-8") as f:
            corpus = [l.strip() for l in f if l.strip()]
        for t, want in zip(corpus, load("upstream_corpus_reel.json")):
            got = hookscore.score_reel(t)
            self.assertEqual({k: got[k] for k in want}, want)
        got = sorted(map(hookscore.score_youtube, corpus), key=lambda r: -r["verdict"])
        self.assertEqual(got, load("upstream_corpus_youtube.json"))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="")
        return subprocess.run([sys.executable, os.path.join(ROOT, "hookscore.py"), *args],
                              capture_output=True, env=env)

    def test_non_ascii_file_does_not_crash_on_any_locale(self):
        p = self.run_cli("--for", "youtube", "--json", HOOKS)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout.decode("utf-8")), load("upstream_youtube.json"))

    def test_reel_json_for_single_hook_is_an_object(self):
        p = self.run_cli("--hook", "$18,000 is what one missing clause cost me.", "--json")
        self.assertEqual(json.loads(p.stdout.decode("utf-8"))["verdict"], "STRONG")

    def test_reel_exit_code_is_1_when_no_hook_is_strong(self):
        p = self.run_cli("--hook", "Hey guys, welcome back to the channel.")
        self.assertEqual(p.returncode, 1)
        self.assertIn(b"DEALBREAKER", p.stdout)


if __name__ == "__main__":
    unittest.main()
