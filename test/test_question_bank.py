
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

from question_bank import load_questions, get_question, check_answer


class QuestionBankTests(unittest.TestCase):

    def test_load_questions(self):
        self.assertEqual(len(load_questions()), 5)

    def test_get_s3_question(self):
        question = get_question("S3")
        self.assertEqual(question["topic"], "S3")
        self.assertEqual(len(question["options"]), 4)
        self.assertNotIn("answer", question)

    def test_difficulty_filter(self):
        question = get_question("S3", "medium")
        self.assertEqual(question["difficulty"], "medium")

    def test_correct_answer(self):
        result = check_answer("s3-003", "C")
        self.assertTrue(result["correct"])

    def test_wrong_answer(self):
        result = check_answer("s3-003", "B")
        self.assertFalse(result["correct"])
        self.assertEqual(result["correct_answer"], "C")

    def test_unknown_topic(self):
        result = get_question("Unknown")
        self.assertIn("error", result)

    def test_unknown_question_id(self):
        result = check_answer("unknown-999", "A")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
