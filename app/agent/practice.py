
import os

from strands import tool
from botocore.exceptions import ClientError

QUESTIONS = {
    "s3": {
        "id": "s3-001",
        "question": "Which S3 feature protects against accidental object deletion?",
        "options": {
            "A": "Transfer Acceleration",
            "B": "Versioning",
            "C": "Static Website Hosting",
            "D": "Requester Pays",
        },
        "answer": "B",
        "explanation": "Versioning preserves multiple versions of an object.",
    },
    "iam": {
        "id": "iam-001",
        "question": "Which principle grants only permissions required for a task?",
        "options": {
            "A": "Least privilege",
            "B": "Full administrator access",
            "C": "Public access",
            "D": "Root account usage",
        },
        "answer": "A",
        "explanation": "Least privilege limits unnecessary permissions.",
    },
}


def make_practice_question(topic: str) -> dict:
    question = QUESTIONS.get(topic.strip().lower())
    if question is None:
        return {"error": f"No questions available for: {topic}"}

    return {
        "id": question["id"],
        "question": question["question"],
        "options": question["options"],
    }


@tool
def generate_practice_question(topic: str) -> dict:
    """Get an AWS certification practice question.

    Args:
        topic: AWS topic, such as S3 or IAM.
    """
    return make_practice_question(topic)


@tool
def check_practice_answer(question_id: str, answer: str) -> dict:
    """Check an answer to an AWS practice question.

    Args:
        question_id: ID returned by generate_practice_question.
        answer: Selected option A, B, C, or D.
    """
    question = next(
        (q for q in QUESTIONS.values() if q["id"] == question_id),
        None,
    )
    if question is None:
        return {"error": "Unknown question ID"}

    selected = answer.strip().upper()
    correct = selected == question["answer"]
    return {
        "correct": correct,
        "correct_answer": question["answer"],
        "explanation": question["explanation"],
    }


def make_lab_task(service: str) -> dict:
    if service.strip().lower() != "s3":
        return {"error": "Only S3 labs are supported currently"}

    return {
        "lab_id": "s3-secure-bucket",
        "title": "Secure an Amazon S3 Bucket",
        "instructions": [
            "Create an S3 bucket with a name starting with study-coach-lab-",
            "Enable bucket Versioning",
            "Enable all four Block Public Access settings",
            "Configure default encryption using SSE-S3 (AES256)",
        ],
        "verification": "Submit the bucket name to verify_lab_task.",
        "cleanup": "Delete test objects and the bucket when finished.",
    }


@tool
def generate_lab_task(service: str) -> dict:
    """Get a hands-on AWS lab task.

    Args:
        service: AWS service name, currently S3.
    """
    return make_lab_task(service)



def verify_s3_lab(bucket_name: str, s3_client, account_id: str) -> dict:
    """Verify S3 lab settings with read-only AWS API calls."""
    expected_region = "eu-central-1"

    if not bucket_name.startswith("study-coach-lab-"):
        return {"error": "Invalid lab bucket name"}

    if not (account_id.isdigit() and len(account_id) == 12):
        return {"error": "A valid 12-digit AWS account ID is required"}

    def read_setting(operation, missing_codes=()):
        try:
            return operation(), None
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in missing_codes:
                return None, None
            if code in ("AccessDenied", "403"):
                return None, "AccessDenied"
            return None, f"AWS error: {code}"
        except Exception as exc:
            return None, f"Verification error: {type(exc).__name__}"

    head, error = read_setting(
        lambda: s3_client.head_bucket(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )
    )
    if error:
        return {"error": error, "check": "bucket_access"}

    region = head.get("BucketRegion")
    if not region:
        region = (
            head.get("ResponseMetadata", {})
            .get("HTTPHeaders", {})
            .get("x-amz-bucket-region")
        )

    if region != expected_region:
        return {
            "error": "Unexpected or unverifiable bucket region",
            "expected_region": expected_region,
            "actual_region": region,
        }

    checks = {}

    versioning, error = read_setting(
        lambda: s3_client.get_bucket_versioning(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )
    )
    if error:
        return {"error": error, "check": "versioning"}

    checks["versioning"] = versioning.get("Status") == "Enabled"

    public, error = read_setting(
        lambda: s3_client.get_public_access_block(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        ),
        missing_codes=("NoSuchPublicAccessBlockConfiguration",),
    )
    if error:
        return {"error": error, "check": "block_public_access"}

    config = (
        public.get("PublicAccessBlockConfiguration", {})
        if public else {}
    )
    flags = (
        "BlockPublicAcls",
        "IgnorePublicAcls",
        "BlockPublicPolicy",
        "RestrictPublicBuckets",
    )
    checks["block_public_access"] = all(
        config.get(flag) is True for flag in flags
    )

    encryption, error = read_setting(
        lambda: s3_client.get_bucket_encryption(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        ),
        missing_codes=("ServerSideEncryptionConfigurationNotFoundError",),
    )
    if error:
        return {"error": error, "check": "default_encryption"}

    rules = (
        encryption.get("ServerSideEncryptionConfiguration", {})
        .get("Rules", [])
        if encryption else []
    )
    checks["default_encryption"] = any(
        rule.get("ApplyServerSideEncryptionByDefault", {})
        .get("SSEAlgorithm") == "AES256"
        for rule in rules
    )

    return {
        "lab_id": "s3-secure-bucket",
        "bucket": bucket_name,
        "region": region,
        "checks": checks,
        "score": sum(checks.values()),
        "total": len(checks),
        "passed": all(checks.values()),
    }

import os
from strands import tool
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

    def test_access_denied_is_not_failed_lab(self):
        from botocore.exceptions import ClientError

        s3 = MagicMock()
        s3.head_bucket.return_value = {
            "BucketRegion": "eu-central-1"
        }
        s3.get_bucket_versioning.side_effect = ClientError(
         {
                "Error": {
                "Code": "AccessDenied",
                "Message": "Access denied"
            }
        },
        "GetBucketVersioning",
        )

        result = verify_s3_lab(
            "study-coach-lab-test", s3, "123456789012"
        )

        self.assertEqual(result["error"], "AccessDenied")
        self.assertEqual(result["check"], "versioning")
        self.assertNotIn("score", result)

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

        s3.head_bucket.return_value = {
            "BucketRegion": "eu-central-1"
        }

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

        s3.head_bucket.return_value = {
            "BucketRegion": "eu-central-1"
        }

        s3.get_bucket_versioning.return_value = {
            "Status": "Suspended"
        }

        s3.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {}
        }

        s3.get_bucket_encryption.return_value = {
            "ServerSideEncryptionConfiguration": {
                "Rules": []
            }
        }

        result = verify_s3_lab(
            "study-coach-lab-test",
            s3,
            "123456789012",
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["total"], 3)

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

@tool
def verify_lab_task(bucket_name: str) -> dict:
    """Verify an S3 lab using read-only AWS API calls.

    Args:
        bucket_name: Name of the S3 lab bucket to verify.
    """
    import boto3

    account_id = os.environ.get("AWS_STUDY_ACCOUNT_ID", "")
    if not account_id:
        return {"error": "AWS_STUDY_ACCOUNT_ID is not configured"}

    s3 = boto3.client("s3")
    return verify_s3_lab(bucket_name, s3, account_id)
