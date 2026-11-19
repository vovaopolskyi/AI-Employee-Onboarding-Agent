
import sys
import unittest
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1] / "app" / "agent"
sys.path.insert(0, str(AGENT_DIR))

from study_materials import find_study_materials


class TestStudyMaterials(unittest.TestCase):

    def test_search_s3(self):
        results = find_study_materials("S3")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["service"], "S3")

    def test_search_iam(self):
        results = find_study_materials("IAM")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["service"], "IAM")

    def test_search_serverless(self):
        results = find_study_materials("serverless")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["service"], "Lambda")

    def test_case_insensitive(self):
        results = find_study_materials("s3")
        self.assertEqual(len(results), 1)

    def test_unknown_topic(self):
        self.assertEqual(find_study_materials("unknownservice"), [])

    def test_empty_query(self):
        self.assertEqual(find_study_materials(""), [])

    def test_result_has_official_url(self):
        results = find_study_materials("S3")
        self.assertTrue(
            results[0]["url"].startswith("https://docs.aws.amazon.com/")
        )


if __name__ == "__main__":
    unittest.main()
