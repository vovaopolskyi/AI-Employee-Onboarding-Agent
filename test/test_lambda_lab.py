
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app" / "agent"),
)

from lambda_lab import make_lambda_lab_task, verify_lambda_lab


ACCOUNT_ID = "123456789012"
FUNCTION_NAME = "study-coach-lab-test"


def mock_lambda_client():
    client = MagicMock()
    client.meta.region_name = "eu-central-1"

    client.get_function_configuration.return_value = {
        "FunctionArn": (
            f"arn:aws:lambda:eu-central-1:{ACCOUNT_ID}:"
            f"function:{FUNCTION_NAME}"
        ),
        "Runtime": "python3.12",
        "MemorySize": 128,
        "Timeout": 10,
        "State": "Active",
        "Role": f"arn:aws:iam::{ACCOUNT_ID}:role/study-coach-lab-role",
    }
    return client


class LambdaLabTests(unittest.TestCase):

    def test_lab_instructions(self):
        lab = make_lambda_lab_task()
        self.assertEqual(lab["lab_id"], "lambda-basic-config")

    def test_valid_configuration(self):
        client = mock_lambda_client()

        result = verify_lambda_lab(
            FUNCTION_NAME, client, ACCOUNT_ID
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["total"], 5)

    def test_wrong_runtime(self):
        client = mock_lambda_client()
        client.get_function_configuration.return_value[
            "Runtime"
        ] = "nodejs22.x"

        result = verify_lambda_lab(
            FUNCTION_NAME, client, ACCOUNT_ID
        )

        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["runtime"])
        self.assertEqual(result["score"], 4)

    def test_wrong_account(self):
        client = mock_lambda_client()

        result = verify_lambda_lab(
            FUNCTION_NAME, client, "999999999999"
        )

        self.assertIn("error", result)

    def test_invalid_name(self):
        client = mock_lambda_client()

        result = verify_lambda_lab(
            "production-function", client, ACCOUNT_ID
        )

        self.assertIn("error", result)
        client.get_function_configuration.assert_not_called()

    def test_wrong_region(self):
        client = mock_lambda_client()
        client.meta.region_name = "us-east-1"

        result = verify_lambda_lab(
            FUNCTION_NAME, client, ACCOUNT_ID
        )

        self.assertIn("error", result)

    def test_access_denied(self):
        client = mock_lambda_client()
        client.get_function_configuration.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            "GetFunctionConfiguration",
        )

        result = verify_lambda_lab(
            FUNCTION_NAME, client, ACCOUNT_ID
        )

        self.assertEqual(result["error"], "AccessDenied")
        self.assertNotIn("score", result)


if __name__ == "__main__":
    unittest.main()
