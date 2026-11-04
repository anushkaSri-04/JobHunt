import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yaml
from engine.fetch import strip_html, parse_ashby, parse_lever, Job
from engine.prefilter import prefilter
from engine.mock import fetch_all_mock

CFG = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config.yaml")))["filters"]


def job(title, loc="Bengaluru"):
    return Job("greenhouse:s:1", "greenhouse", "C", title, loc, "u", "")


def kept(title, loc="Bengaluru"):
    return bool(prefilter([job(title, loc)], CFG))


class Parsers(unittest.TestCase):
    def test_greenhouse_double_escape(self):
        self.assertEqual(strip_html("&lt;p&gt;A &amp;amp; B&lt;/p&gt;"), "A & B")

    def test_lever_full_jd_concatenated(self):
        j = [x for x in fetch_all_mock() if x.ats == "lever" and x.title.startswith("Backend")][0]
        for part in ("market data pipeline", "Kubernetes", "pair-programming"):
            self.assertIn(part, j.description)

    def test_lever_epoch_ms(self):
        j = parse_lever("s", "C", [{"id": "1", "text": "x", "createdAt": 1700000000000}])[0]
        self.assertTrue(j.posted_at.startswith("2023-11"))

    def test_ashby_skips_unlisted(self):
        self.assertEqual([j.job_id for j in parse_ashby("s", "C", {"jobs": [
            {"id": "a", "isListed": False}, {"id": "b"}]})], ["ashby:s:b"])


class Prefilter(unittest.TestCase):
    def test_sde_variants(self):
        self.assertTrue(kept("SDE 1"))
        self.assertTrue(kept("SDE-1"))
        self.assertTrue(kept("Software Development Engineer I"))
        self.assertFalse(kept("SDE2"))          # mid-level, excluded by design

    def test_exclusions(self):
        for t in ("Senior Backend Engineer", "Java Backend Engineer",
                  "Software Engineer II", "Full Stack Engineer"):
            self.assertFalse(kept(t), t)

    def test_location_gate(self):
        self.assertFalse(kept("Software Engineer", "Berlin"))
        self.assertTrue(kept("Software Engineer", "Pune, India"))

    def test_mock_funnel_dedupes_ids_and_drops_junk(self):
        jobs = fetch_all_mock()
        self.assertEqual(len({j.job_id for j in jobs}), len(jobs))
        titles = {j.title for j in prefilter(jobs, CFG)}
        self.assertIn("Software Development Engineer, Core Infra", titles)
        self.assertNotIn("Enterprise Account Executive", titles)
        self.assertNotIn("Staff Software Engineer, Storage", titles)

    def test_real_feed_leaks_dropped(self):
        for t in ("Partnerships Associate", "Associate - Founder's Office",
                "Information Security Compliance Intern",
                "Software Development Engineer in Test (SDET)",
                "Software Engineer (C++)", "Software Engineer 2 , Applied AI",
                "Software Engineer – Automation & ServiceNow"):
            self.assertFalse(kept(t), t)

    def test_real_feed_keepers_survive(self):
        for t in ("Machine Learning Intern", "Software Development Engineer Intern",
                "Software Engineer- Python", "Data Engineer", "AI Engineer"):
            self.assertTrue(kept(t), t)


if __name__ == "__main__":
    unittest.main()