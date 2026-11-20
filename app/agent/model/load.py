
import os

from strands.models.bedrock import BedrockModel


DEFAULT_MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_REGION = "eu-central-1"


def load_model() -> BedrockModel:
    """Create the Bedrock model used by AWS Study Coach."""
    return BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
        region_name=os.getenv("AWS_REGION", DEFAULT_REGION),
        temperature=0.2,
        max_tokens=1024,
    )
