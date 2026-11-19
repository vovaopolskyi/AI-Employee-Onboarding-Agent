
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

from iam_lab import (
    LAB_POLICY,
    LAB_ROLE,
    make_iam_lab_task,
    verify_iam_lab,
)


ACCOUNT = "123456789012"


def mock_iam():
    client = MagicMock()

    client.get_role.return_value = {
        "Role": {
            "Arn": f"arn:aws:iam::{ACCOUNT}:role/{LAB_ROLE}",
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }]
            },
        }
    }

    client.list_role_policies.return_value = {
        "PolicyNames": [LAB_POLICY]
    }

    client.list_attached_role_policies.return_value = {
        "AttachedPolicies": []
    }

    client.get_role_policy.return_value = {
        "PolicyDocument": {
            "Statement": [{
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": (
                    f"arn:aws:s3:::study-coach-lab-{ACCOUNT}-euc1/*"
                ),
            }]
        }
    }
    return client


class IAMLabTests(unittest.TestCase):

    def test_lab_instructions(self):
        lab = make_iam_lab_task()
        self.assertEqual(lab["lab_id"], "iam-least-privilege")

    def test_valid_role(self):
        result = verify_iam_lab(LAB_ROLE, mock_iam(), ACCOUNT)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 5)

    def test_reject_wildcard_actions(self):
        client = mock_iam()
        client.get_role_policy.return_value[
            "PolicyDocument"
        ]["Statement"][0]["Action"] = "s3:*"

        result = verify_iam_lab(LAB_ROLE, client, ACCOUNT)
        self.assertFalse(result["checks"]["least_privilege_action"])

    def test_reject_wildcard_resources(self):
        client = mock_iam()
        client.get_role_policy.return_value[
            "PolicyDocument"
        ]["Statement"][0]["Resource"] = "*"

        result = verify_iam_lab(LAB_ROLE, client, ACCOUNT)
        self.assertFalse(result["checks"]["scoped_s3_resource"])

    def test_reject_attached_policies(self):
        client = mock_iam()
        client.list_attached_role_policies.return_value = {
            "AttachedPolicies": [{
                "PolicyName": "AdministratorAccess",
                "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
            }]
        }

        result = verify_iam_lab(LAB_ROLE, client, ACCOUNT)
        self.assertFalse(result["checks"]["no_attached_policies"])

    def test_reject_wrong_trust(self):
        client = mock_iam()
        client.get_role.return_value["Role"][
            "AssumeRolePolicyDocument"
        ]["Statement"][0]["Principal"]["Service"] = "ec2.amazonaws.com"

        result = verify_iam_lab(LAB_ROLE, client, ACCOUNT)
        self.assertFalse(result["checks"]["trust_policy"])

    def test_invalid_role_name(self):
        client = mock_iam()
        result = verify_iam_lab(
            "production-admin-role", client, ACCOUNT
        )
        self.assertIn("error", result)
        client.get_role.assert_not_called()

    def test_access_denied(self):
        client = mock_iam()
        client.get_role.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied",
                }
            },
            "GetRole",
        )

        result = verify_iam_lab(LAB_ROLE, client, ACCOUNT)
        self.assertEqual(result["error"], "AccessDenied")
        self.assertNotIn("score", result)


if __name__ == "__main__":
    unittest.main()
