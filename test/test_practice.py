
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

from practice import (
    make_practice_question,
    make_lab_task,
    verify_s3_lab,
)


class PracticeTests(unittest.TestCase):

    def test_s3_question(self):
        result = make_practice_question("S3")
        self.assertEqual(result["id"], "s3-001")
        self.assertEqual(len(result["options"]), 4)
        self.assertNotIn("answer", result)

    def test_iam_question(self):
        result = make_practice_question("IAM")
        self.assertEqual(result["id"], "iam-001")

    def test_unknown_question(self):
        self.assertIn("error", make_practice_question("EC2"))

    def test_s3_lab(self):
        result = make_lab_task("S3")
        self.assertEqual(result["lab_id"], "s3-secure-bucket")
        self.assertEqual(len(result["instructions"]), 4)

    def test_unknown_lab(self):
        self.assertIn("error", make_lab_task("VPC"))

    def test_s3_lab_pass(self):
        s3 = MagicMock()

        s3.get_bucket_versioning.return_value = {
            "Status": "Enabled"
        }
        s3.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        }
        s3.get_bucket_encryption.return_value = {
            "ServerSideEncryptionConfiguration": {
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }
        }

        result = verify_s3_lab(
            "study-coach-lab-test",
            s3,
            "123456789012",
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 3)
        self.assertEqual(result["total"], 3)
        s3.head_bucket.assert_called_once_with(
            Bucket="study-coach-lab-test",
            ExpectedBucketOwner="123456789012",
        )

    def test_s3_lab_failure(self):
        s3 = MagicMock()
        s3.get_bucket_versioning.return_value = {
            "Status": "Suspended"
        }
        s3.get_public_access_block.side_effect = Exception("Missing")
        s3.get_bucket_encryption.side_effect = Exception("Missing")

        result = verify_s3_lab(
            "study-coach-lab-test",
            s3,
            "123456789012",
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["score"], 0)

    def test_reject_wrong_bucket_prefix(self):
        s3 = MagicMock()
        result = verify_s3_lab("production-bucket", s3, "123456789012")
        self.assertIn("error", result)
        s3.head_bucket.assert_not_called()

    def test_reject_invalid_account_id(self):
        result = verify_s3_lab(
            "study-coach-lab-test",
            MagicMock(),
            "invalid",
        )
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
