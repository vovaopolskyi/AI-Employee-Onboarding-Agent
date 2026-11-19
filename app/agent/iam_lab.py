
import json
import os
import re
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError
from strands import tool


LAB_ROLE = "study-coach-lab-s3-reader"
LAB_POLICY = "StudyCoachLabS3ReadPolicy"


def parse_document(value):
    if isinstance(value, dict):
        return value
    return json.loads(unquote(value))


def make_iam_lab_task() -> dict:
    return {
        "lab_id": "iam-least-privilege",
        "service": "IAM",
        "title": "Create a Least-Privilege IAM Role",
        "role_name": LAB_ROLE,
        "instructions": [
            "Create an IAM role named study-coach-lab-s3-reader",
            "Set its trusted service to lambda.amazonaws.com",
            "Add one inline policy named StudyCoachLabS3ReadPolicy",
            "Allow only s3:GetObject on the designated lab bucket objects",
            "Do not attach additional managed or inline policies",
        ],
        "verification": "Use verify_iam_lab_task to check the role.",
    }


def verify_iam_lab(role_name: str, iam_client, account_id: str) -> dict:
    if role_name != LAB_ROLE:
        return {"error": "Unexpected IAM lab role name"}

    if not re.fullmatch(r"\d{12}", account_id):
        return {"error": "Invalid AWS account ID"}

    bucket = f"study-coach-lab-{account_id}-euc1"
    expected_resource = f"arn:aws:s3:::{bucket}/*"

    try:
        role = iam_client.get_role(RoleName=role_name)["Role"]

        inline_response = iam_client.list_role_policies(
            RoleName=role_name
        )
        attached_response = iam_client.list_attached_role_policies(
            RoleName=role_name
        )

        if (
            inline_response.get("IsTruncated", False)
            or attached_response.get("IsTruncated", False)
        ):
            return {"error": "Incomplete IAM policy listing"}

        inline_names = inline_response.get("PolicyNames", [])
        attached = attached_response.get("AttachedPolicies", [])

        policy = None
        if LAB_POLICY in inline_names:
            policy = parse_document(
                iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=LAB_POLICY,
                )["PolicyDocument"]
            )

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")

        if code in ("AccessDenied", "AccessDeniedException"):
            return {"error": "AccessDenied", "check": "iam_access"}
        if code == "NoSuchEntity":
            return {"error": "IAM role or lab policy not found"}

        return {"error": "AWS API error", "code": code}
    except (ValueError, TypeError, KeyError):
        return {"error": "Invalid IAM policy document"}

    expected_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    if role.get("Arn") != expected_arn:
        return {"error": "IAM role account or ARN mismatch"}

    try:
        trust = parse_document(role["AssumeRolePolicyDocument"])
    except (ValueError, TypeError, KeyError):
        return {"error": "Invalid trust policy"}

    expected_trust = {
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }

    trust_statements = trust.get("Statement", [])
    if isinstance(trust_statements, dict):
        trust_statements = [trust_statements]

    trust_ok = (
        isinstance(trust_statements, list)
        and len(trust_statements) == 1
        and trust_statements[0] == expected_trust
    )

    permission_ok = False
    resource_ok = False

    if policy is not None:
        statements = policy.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        if isinstance(statements, list) and len(statements) == 1:
            statement = statements[0]

            permission_ok = (
                statement.get("Effect") == "Allow"
                and statement.get("Action") == "s3:GetObject"
                and set(statement.keys()).issubset(
                    {"Sid", "Effect", "Action", "Resource"}
                )
            )

            resource_ok = (
                statement.get("Resource") == expected_resource
            )

    checks = {
        "trust_policy": trust_ok,
        "single_inline_policy": inline_names == [LAB_POLICY],
        "no_attached_policies": len(attached) == 0,
        "least_privilege_action": permission_ok,
        "scoped_s3_resource": resource_ok,
    }

    return {
        "lab_id": "iam-least-privilege",
        "role": role_name,
        "checks": checks,
        "score": sum(checks.values()),
        "total": len(checks),
        "passed": all(checks.values()),
    }


@tool
def generate_iam_lab_task() -> dict:
    """Get the IAM least-privilege hands-on lab."""
    return make_iam_lab_task()


@tool
def verify_iam_lab_task(role_name: str) -> dict:
    """Verify an IAM lab role using read-only AWS APIs.

    Args:
        role_name: Name of the designated IAM lab role.
    """
    account_id = os.environ.get("AWS_STUDY_ACCOUNT_ID", "")

    if not account_id:
        return {"error": "AWS_STUDY_ACCOUNT_ID is not configured"}

    iam = boto3.client("iam")

    return verify_iam_lab(role_name, iam, account_id)
