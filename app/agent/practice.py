
import os

from strands import tool


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
    """Verify a lab bucket with read-only AWS API calls."""
    if not bucket_name.startswith("study-coach-lab-"):
        return {"error": "Bucket name must start with study-coach-lab-"}

    if not (account_id.isdigit() and len(account_id) == 12):
        return {"error": "A valid 12-digit AWS account ID is required"}

    checks = {}

    try:
        s3_client.head_bucket(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )
    except Exception:
        return {"error": "Cannot access bucket or verify its owner"}

    try:
        versioning = s3_client.get_bucket_versioning(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )
        checks["versioning"] = versioning.get("Status") == "Enabled"
    except Exception:
        checks["versioning"] = False

    try:
        public = s3_client.get_public_access_block(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )["PublicAccessBlockConfiguration"]

        required_flags = (
            "BlockPublicAcls",
            "IgnorePublicAcls",
            "BlockPublicPolicy",
            "RestrictPublicBuckets",
        )
        checks["block_public_access"] = all(
            public.get(flag) is True for flag in required_flags
        )
    except Exception:
        checks["block_public_access"] = False

    try:
        encryption = s3_client.get_bucket_encryption(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
        )
        rules = encryption["ServerSideEncryptionConfiguration"]["Rules"]
        checks["default_encryption"] = any(
            rule["ApplyServerSideEncryptionByDefault"].get("SSEAlgorithm")
            == "AES256"
            for rule in rules
        )
    except Exception:
        checks["default_encryption"] = False

    return {
        "lab_id": "s3-secure-bucket",
        "bucket": bucket_name,
        "checks": checks,
        "score": sum(checks.values()),
        "total": len(checks),
        "passed": all(checks.values()),
    }


@tool
def verify_lab_task(bucket_name: str) -> dict:
    """Verify a hands-on S3 lab using read-only AWS API calls.

    Requires AWS_STUDY_ACCOUNT_ID and IAM read permissions.

    Args:
        bucket_name: Name of the S3 lab bucket to verify.
    """
    import boto3

    account_id = os.environ.get("AWS_STUDY_ACCOUNT_ID", "")
    if not account_id:
        return {"error": "AWS_STUDY_ACCOUNT_ID is not configured"}

    s3 = boto3.client("s3")
    return verify_s3_lab(bucket_name, s3, account_id)
