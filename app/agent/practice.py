
import os

from strands import tool
from botocore.exceptions import ClientError
from question_bank import get_question, check_answer




def make_practice_question(topic: str) -> dict:
    return get_question(topic)


@tool
def generate_practice_question(
    topic: str,
    difficulty: str = "any",
) -> dict:
    """Get a random AWS certification practice question.

    Args:
        topic: AWS topic, such as S3.
        difficulty: easy, medium, or any.
    """
    return get_question(topic, difficulty)


@tool
def check_practice_answer(question_id: str, answer: str) -> dict:
    """Check an answer to an AWS certification question.

    Args:
        question_id: ID returned by generate_practice_question.
        answer: Selected option A, B, C, or D.
    """
    return check_answer(question_id, answer)

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
