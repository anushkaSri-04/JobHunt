import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine.skills import find_skills, extract, min_years, analyze, canonical


class Dictionary(unittest.TestCase):
    def test_aliases_map_to_canonical(self):
        self.assertEqual(find_skills("we run k8s and Postgres"), {"Kubernetes", "PostgreSQL"})
        self.assertIn("MCP", find_skills("Model Context Protocol (MCP)"))
        self.assertIn("REST", find_skills("REST APIs"))

    def test_word_boundaries(self):
        self.assertEqual(find_skills("JavaScript"), {"JavaScript"})            # not Java
        self.assertNotIn("SQL", find_skills("PostgreSQL"))                    # not SQL
        self.assertNotIn("JavaScript", find_skills("Node.js"))                 # '.js' is not 'js'
        self.assertIn("C++", find_skills("C++ and C#")); self.assertIn("C#", find_skills("C++ and C#"))

    def test_case_sensitive_spellings(self):
        self.assertIn("React", find_skills("Experience with React"))
        self.assertNotIn("React", find_skills("react quickly to incidents"))
        self.assertNotIn("Go", find_skills("Go beyond the brief"))
        self.assertIn("Go", find_skills("We write golang services"))

    def test_canonical_lookup(self):
        self.assertEqual(canonical("postgresql"), "PostgreSQL")
        self.assertIsNone(canonical("cobol"))


class Sections(unittest.TestCase):
    def test_required_vs_nice_sections(self):
        jd = "Requirements\n- Python\n- Docker\nNice to have\n- Kubernetes\n"
        self.assertEqual(extract(jd), ({"Python", "Docker"}, {"Kubernetes"}))

    def test_inline_heading_with_colon(self):
        req, nice = extract("Must have: Python, SQL\nNice to have: Kafka, Redis")
        self.assertEqual(req, {"Python", "SQL"}); self.assertEqual(nice, {"Kafka", "Redis"})

    def test_inline_cue_in_required_section(self):
        req, nice = extract("Requirements\nPython\nExperience with Kafka is a plus")
        self.assertEqual((req, nice), ({"Python"}, {"Kafka"}))

    def test_about_company_is_ignored(self):
        jd = "About us\nWe run on Kubernetes and Kafka.\nRequirements\nPython"
        self.assertEqual(extract(jd), ({"Python"}, set()))

    def test_default_is_required(self):
        self.assertEqual(extract("Build APIs in Python."), ({"Python"}, set()))

    def test_required_wins_over_nice(self):
        req, nice = extract("Requirements\nPython\nNice to have\nPython, Go (golang)")
        self.assertIn("Python", req); self.assertNotIn("Python", nice)


class Years(unittest.TestCase):
    def test_years(self):
        self.assertEqual(min_years("5+ years of experience in backend"), 5)
        self.assertEqual(min_years("Experience: 2-4 years"), 2)
        self.assertEqual(min_years("0-2 years experience"), 0)
        self.assertIsNone(min_years("We are 10 years old. Join us."))
        self.assertIsNone(min_years("No experience stated"))


class Matching(unittest.TestCase):
    def test_weighted_percentage(self):
        jd = "Requirements\nPython\nDocker\nNice to have\nKubernetes"
        a = analyze(jd, {"Python"})            
        self.assertEqual(a["pct"], 0.4)
        self.assertEqual(a["skills"]["req_missing"], ["Docker"])
        self.assertEqual(a["skills"]["nice_missing"], ["Kubernetes"])
        self.assertEqual(analyze(jd, {"Python", "Docker", "Kubernetes"})["pct"], 1.0)

    def test_no_known_skills_is_unscored(self):
        self.assertIsNone(analyze("Join our friendly team!", {"Python"})["pct"])


if __name__ == "__main__":
    unittest.main()