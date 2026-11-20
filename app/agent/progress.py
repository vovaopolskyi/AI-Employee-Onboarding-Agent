
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from strands import tool


PROGRESS_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "student_progress.json"
)

PROGRESS_LOCK = Lock()


def _load_data():
    if not PROGRESS_FILE.exists():
        return {"exams": []}

    with PROGRESS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(
        data.get("exams"), list
    ):
        raise ValueError("Invalid student progress file")

    return data


def _write_data(data):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PROGRESS_FILE.parent,
            prefix=".progress-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")

        os.replace(temp_path, PROGRESS_FILE)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def save_exam_result(session_id: str, result: dict) -> dict:
    """Save a completed exam once.

    This is a single-student local development store.
    """
    if result.get("status") != "completed":
        raise ValueError("Only completed exams can be saved")

    with PROGRESS_LOCK:
        data = _load_data()

        if any(
            item["session_id"] == session_id
            for item in data["exams"]
        ):
            return {"saved": False, "reason": "already_exists"}

        record = {
            "session_id": session_id,
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "score": result["score"],
            "total": result["total"],
            "percentage": result["percentage"],
            "passed": result["passed"],
            "results": result["results"],
        }

        data["exams"].append(record)
        _write_data(data)

    return {"saved": True, "session_id": session_id}


def get_progress_summary() -> dict:
    """Return statistics for locally saved exams."""
    with PROGRESS_LOCK:
        data = _load_data()

    exams = data["exams"]

    if not exams:
        return {
            "total_exams": 0,
            "total_questions": 0,
            "correct_answers": 0,
            "overall_accuracy": 0.0,
            "passed_exams": 0,
            "topics": {},
            "recent_exams": [],
        }

    total_questions = sum(e["total"] for e in exams)
    correct_answers = sum(e["score"] for e in exams)

    topics = {}

    for exam in exams:
        for item in exam["results"]:
            topic = item["topic"]

            if topic not in topics:
                topics[topic] = {
                    "correct": 0,
                    "total": 0,
                }

            topics[topic]["total"] += 1
            topics[topic]["correct"] += int(item["correct"])

    for stats in topics.values():
        stats["accuracy"] = round(
            100 * stats["correct"] / stats["total"], 1
        )

    recent = [
        {
            "completed_at": exam["completed_at"],
            "score": exam["score"],
            "total": exam["total"],
            "percentage": exam["percentage"],
            "passed": exam["passed"],
        }
        for exam in exams[-5:]
    ]

    return {
        "total_exams": len(exams),
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "overall_accuracy": round(
            100 * correct_answers / total_questions, 1
        ),
        "passed_exams": sum(e["passed"] for e in exams),
        "topics": topics,
        "recent_exams": list(reversed(recent)),
    }


@tool
def get_student_progress() -> dict:
    """Show local AWS certification practice exam progress."""
    return get_progress_summary()
