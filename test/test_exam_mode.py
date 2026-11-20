
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

from exam_mode import (
    EXAMS,
    start_exam,
    submit_answer,
    finish_exam,
)


class ExamModeTests(unittest.TestCase):

    def setUp(self):
        EXAMS.clear()

    def test_start_exam(self):
        exam = start_exam("all", 10)

        self.assertIn("session_id", exam)
        self.assertEqual(exam["question"]["number"], 1)
        self.assertNotIn("answer", exam["question"])

    def test_topic_filter(self):
        exam = start_exam("IAM", 3)

        self.assertEqual(exam["question"]["topic"], "IAM")

    def test_too_many_questions(self):
        exam = start_exam("S3", 20)

        self.assertIn("error", exam)

    def test_invalid_count(self):
        self.assertIn("error", start_exam("all", 0))

    def test_submit_answer(self):
        exam = start_exam("S3", 2)
        session_id = exam["session_id"]
        question_id = exam["question"]["id"]

        result = submit_answer(session_id, question_id, "A")

        self.assertEqual(result["answered"], 1)
        self.assertNotIn("correct_answer", result)
        self.assertNotIn("correct_answer", result["question"])

    def test_reject_wrong_question(self):
        exam = start_exam("S3", 2)

        result = submit_answer(
            exam["session_id"],
            "wrong-question",
            "A",
        )

        self.assertIn("error", result)

    def test_cannot_finish_early(self):
        exam = start_exam("S3", 2)

        result = finish_exam(exam["session_id"])

        self.assertIn("error", result)

    def test_complete_exam(self):
        exam = start_exam("S3", 2)
        session_id = exam["session_id"]

        for question in EXAMS[session_id]["questions"]:
            result = submit_answer(
                session_id,
                question["id"],
                question["answer"],
            )

        self.assertEqual(result["status"], "ready_to_finish")

        finished = finish_exam(session_id)

        self.assertEqual(finished["score"], 2)
        self.assertEqual(finished["percentage"], 100.0)
        self.assertTrue(finished["passed"])
        self.assertEqual(len(finished["results"]), 2)

    def test_cannot_finish_twice(self):
        exam = start_exam("S3", 1)
        session_id = exam["session_id"]
        question = EXAMS[session_id]["questions"][0]

        submit_answer(
            session_id,
            question["id"],
            question["answer"],
        )
        finish_exam(session_id)

        self.assertIn("error", finish_exam(session_id))


if __name__ == "__main__":
    unittest.main()
