
import os
import re

import boto3
from botocore.exceptions import ClientError
from strands import tool


LAB_PREFIX = "study-coach-lab-"
LAB_REGION = "eu-central-1"


def make_lambda_lab_task() -> dict:
    return {
        "lab_id": "lambda-basic-config",
        "service": "Lambda",
        "title": "Configure a Secure AWS Lambda Function",
        "instructions": [
            "Create a Lambda function named study-coach-lab-*",
            "Select the Python 3.12 runtime",
            "Configure memory to 128 MB",
            "Configure timeout to 10 seconds",
            "Ensure the function is in Active state",
            "Use an execution role from your AWS account",
        ],
        "region": LAB_REGION,
        "verification": "Submit the function name to verify_lambda_lab_task.",
        "cleanup": "Delete the lab function and its dedicated role after testing.",
    }


def verify_lambda_lab(
    function_name: str,
    lambda_client,
    account_id: str,
) -> dict:
    """Read-only verification of a lab Lambda configuration."""

    if not re.fullmatch(r"study-coach-lab-[a-zA-Z0-9-_]+", function_name):
        return {"error": "Invalid Lambda lab function name"}

    if not re.fullmatch(r"\d{12}", account_id):
        return {"error": "Invalid AWS account ID"}

    if lambda_client.meta.region_name != LAB_REGION:
        return {
            "error": "Unexpected AWS client region",
            "expected_region": LAB_REGION,
        }

    try:
        config = lambda_client.get_function_configuration(
            FunctionName=function_name,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")

        if code in ("AccessDeniedException", "AccessDenied"):
            return {"error": "AccessDenied", "check": "lambda_access"}
        if code == "ResourceNotFoundException":
            return {"error": "Lambda function not found"}

        return {"error": "AWS API error", "code": code}
    except Exception as exc:
        return {"error": "Verification unavailable", "type": type(exc).__name__}

    expected_arn = (
        f"arn:aws:lambda:{LAB_REGION}:{account_id}:"
        f"function:{function_name}"
    )

    if config.get("FunctionArn") != expected_arn:
        return {"error": "Function ARN, account, or region mismatch"}

    role_arn = config.get("Role", "")
    role_prefix = f"arn:aws:iam::{account_id}:role/"

    checks = {
        "runtime": config.get("Runtime") == "python3.12",
        "memory": config.get("MemorySize") == 128,
        "timeout": config.get("Timeout") == 10,
        "state": config.get("State") == "Active",
        "execution_role": (
            role_arn.startswith(role_prefix)
            and len(role_arn) > len(role_prefix)
        ),
    }

    return {
        "lab_id": "lambda-basic-config",
        "function": function_name,
        "region": LAB_REGION,
        "checks": checks,
        "score": sum(checks.values()),
        "total": len(checks),
        "passed": all(checks.values()),
    }


@tool
def generate_lambda_lab_task() -> dict:
    """Get the hands-on AWS Lambda configuration lab."""
    return make_lambda_lab_task()


@tool
def verify_lambda_lab_task(function_name: str) -> dict:
    """Verify a lab Lambda configuration using read-only AWS APIs.

    Args:
        function_name: Name of a study-coach-lab-* Lambda function.
    """
    account_id = os.environ.get("AWS_STUDY_ACCOUNT_ID", "")

    if not account_id:
        return {"error": "AWS_STUDY_ACCOUNT_ID is not configured"}

    client = boto3.client("lambda", region_name=LAB_REGION)

    return verify_lambda_lab(
        function_name,
        client,
        account_id,
    )
