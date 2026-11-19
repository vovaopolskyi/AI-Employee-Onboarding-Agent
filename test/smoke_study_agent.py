import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1] / "app" / "agent"
sys.path.insert(0, str(AGENT_DIR))

from main import _get_agent


def main():
    agent = _get_agent("smoke-study-session", "smoke-test-user")

    result = agent(
        "Use search_study_materials to find official AWS S3 "
        "documentation. Return its title and URL."
    )

    answer = str(result)

    assert "Amazon S3 User Guide" in answer
    assert "https://docs.aws.amazon.com/AmazonS3/latest/userguide/" in answer

    print("PASS: Study Coach integration smoke test")


if __name__ == "__main__":
    main()