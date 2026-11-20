
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

import progress
from exam_mode import EXAMS, start_exam, submit_answer, finish_exam


class ProgressTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        patcher = patch.object(
            progress,
            "PROGRESS_FILE",
            Path(self.temp_dir.name) / "progress.json",
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        EXAMS.clear()

    def example_result(self):
        return {
            "status": "completed",
            "score": 1,
            "total": 2,
            "percentage": 50.0,
            "passed": False,
            "results": [
                {"topic": "S3", "correct": True},
                {"topic": "IAM", "correct": False},
            ],
        }

    def test_empty_progress(self):
        summary = progress.get_progress_summary()

        self.assertEqual(summary["total_exams"], 0)
        self.assertEqual(summary["overall_accuracy"], 0.0)

    def test_save_exam(self):
        saved = progress.save_exam_result(
            "session-1",
            self.example_result(),
        )

        self.assertTrue(saved["saved"])
        self.assertTrue(progress.PROGRESS_FILE.exists())

    def test_duplicate_exam_not_saved(self):
        result = self.example_result()

        progress.save_exam_result("session-1", result)
        duplicate = progress.save_exam_result("session-1", result)

        self.assertFalse(duplicate["saved"])
        self.assertEqual(
            progress.get_progress_summary()["total_exams"],
            1,
        )

    def test_progress_statistics(self):
        progress.save_exam_result(
            "session-1",
            self.example_result(),
        )
        progress.save_exam_result(
            "session-2",
            self.example_result(),
        )

        summary = progress.get_progress_summary()

        self.assertEqual(summary["total_exams"], 2)
        self.assertEqual(summary["total_questions"], 4)
        self.assertEqual(summary["correct_answers"], 2)
        self.assertEqual(summary["overall_accuracy"], 50.0)
        self.assertEqual(summary["topics"]["S3"]["accuracy"], 100.0)
        self.assertEqual(summary["topics"]["IAM"]["accuracy"], 0.0)

    def test_exam_completion_saves_progress(self):
        exam = start_exam("S3", 2)
        session_id = exam["session_id"]

        for question in EXAMS[session_id]["questions"]:
            submit_answer(
                session_id,
                question["id"],
                question["answer"],
            )

        finished = finish_exam(session_id)
        summary = progress.get_progress_summary()

        self.assertEqual(finished["score"], 2)
        self.assertEqual(summary["total_exams"], 1)
        self.assertEqual(summary["overall_accuracy"], 100.0)


if __name__ == "__main__":
    unittest.main()
