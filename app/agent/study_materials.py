
from strands import tool

STUDY_MATERIALS = [
    {
        "service": "S3",
        "title": "Amazon S3 User Guide",
        "topics": ["storage", "buckets", "objects", "versioning"],
        "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/",
    },
    {
        "service": "IAM",
        "title": "AWS IAM User Guide",
        "topics": ["security", "identity", "roles", "policies", "permissions"],
        "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/",
    },
    {
        "service": "Lambda",
        "title": "AWS Lambda Developer Guide",
        "topics": ["serverless", "functions", "events", "compute"],
        "url": "https://docs.aws.amazon.com/lambda/latest/dg/",
    },
]


def find_study_materials(query: str) -> list[dict]:
    """Search the curated AWS study catalog by keyword."""
    keywords = query.lower().strip().split()

    if not keywords:
        return []

    results = []

    for material in STUDY_MATERIALS:
        searchable_text = " ".join([
            material["service"],
            material["title"],
            *material["topics"],
        ]).lower()

        if any(keyword in searchable_text for keyword in keywords):
            results.append(material)

    return results


@tool
def search_study_materials(query: str) -> list[dict]:
    """Search curated AWS certification study materials.

    Args:
        query: AWS service or topic, such as S3, IAM, or serverless.

    Returns:
        Matching study resources with official documentation URLs.
    """
    return find_study_materials(query)
