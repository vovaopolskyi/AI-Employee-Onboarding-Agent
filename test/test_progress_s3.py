import hashlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "agent"))
import progress
import progress_s3


class S3ProgressTests(unittest.TestCase):
    def setUp(self):
        self.s3 = MagicMock()
        patcher = patch.object(progress_s3, "client", return_value=self.s3)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_conditional_save_and_duplicate(self):
        record = {"session_id": "exam-1", "score": 1}
        self.assertTrue(progress_s3.save_record("progress-bucket", "exam-1", record)["saved"])
        args = self.s3.put_object.call_args.kwargs
        self.assertEqual(args["IfNoneMatch"], "*")
        self.assertEqual(args["Key"], "progress/exams/" + hashlib.sha256(b"exam-1").hexdigest() + ".json")
        self.assertEqual(json.loads(args["Body"]), record)
        self.s3.put_object.side_effect = ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        self.assertFalse(progress_s3.save_record("progress-bucket", "exam-1", record)["saved"])

    def test_access_errors_do_not_become_duplicate_or_empty_history(self):
        self.s3.put_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        with self.assertRaises(ClientError):
            progress_s3.save_record("progress-bucket", "exam-1", {})
        self.s3.get_paginator.return_value.paginate.side_effect = RuntimeError("unavailable")
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            progress_s3.load_records("progress-bucket")

    def test_loads_every_page_and_closes_bodies(self):
        paginator = self.s3.get_paginator.return_value
        paginator.paginate.return_value = [{"Contents": [{"Key": "first"}]}, {"Contents": [{"Key": "second"}]}]
        bodies = [io.BytesIO(json.dumps({"session_id": key}).encode()) for key in ("first", "second")]
        self.s3.get_object.side_effect = [{"Body": body} for body in bodies]
        self.assertEqual(progress_s3.load_records("progress-bucket"), [{"session_id": "first"}, {"session_id": "second"}])
        self.assertTrue(all(body.closed for body in bodies))
        paginator.paginate.assert_called_once_with(Bucket="progress-bucket", Prefix="progress/exams/")

    def test_empty_bucket(self):
        self.s3.get_paginator.return_value.paginate.return_value = [{}]
        self.assertEqual(progress_s3.load_records("progress-bucket"), [])

    def test_cloud_routing_does_not_touch_local_file(self):
        result = {"status": "completed", "score": 1, "total": 1, "percentage": 100.0, "passed": True, "results": []}
        with patch.dict(os.environ, {"PROGRESS_S3_BUCKET": "progress-bucket"}), patch.object(progress, "_write_data") as local_write:
            self.assertTrue(progress.save_exam_result("exam-1", result)["saved"])
            local_write.assert_not_called()

    def test_cloud_results_are_sorted_by_completion_time(self):
        records = [{"completed_at": f"2026-11-{day:02d}", "total": 1, "score": 1, "passed": True, "percentage": 100, "results": []} for day in (3, 1, 2)]
        with patch.dict(os.environ, {"PROGRESS_S3_BUCKET": "progress-bucket"}), patch.object(progress_s3, "load_records", return_value=records):
            summary = progress.get_progress_summary()
        self.assertEqual(summary["recent_exams"][0]["completed_at"], "2026-11-03")
        self.assertEqual(summary["total_exams"], 3)


if __name__ == "__main__":
    unittest.main()
