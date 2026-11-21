import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

AGENT_DIR = Path(__file__).resolve().parents[1] / "app" / "agent"
sys.path.insert(0, str(AGENT_DIR))

from main import _get_agent
from exam_mode import EXAMS
import progress


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def tool_calls(agent, since=0):
    return [
        block["toolUse"]["name"]
        for message in agent.messages[since:]
        for block in message.get("content", [])
        if "toolUse" in block
    ]


def tool_outputs(agent, since=0):
    names = {
        block["toolUse"]["toolUseId"]: block["toolUse"]["name"]
        for message in agent.messages[since:]
        for block in message.get("content", [])
        if "toolUse" in block
    }
    outputs = {}
    for message in agent.messages[since:]:
        for block in message.get("content", []):
            if "toolResult" not in block:
                continue
            result = block["toolResult"]
            require(result.get("status") != "error", "Tool execution failed")
            for content in result.get("content", []):
                if "text" in content:
                    outputs[names[result["toolUseId"]]] = json.loads(content["text"])
    return outputs


def check_study_materials(agent):
    before = len(agent.messages)

    result = agent(
        "Use search_study_materials to find official AWS S3 "
        "documentation. Return its title and URL."
    )

    answer = str(result)

    require("search_study_materials" in tool_calls(agent, before),
            "Agent did not call the study materials tool")
    require("Amazon S3 User Guide" in answer, "Missing documentation title")
    require("https://docs.aws.amazon.com/AmazonS3/latest/userguide/" in answer,
            "Missing official documentation URL")

    print("PASS: study materials search")


def check_exam(agent):
    existing_sessions = set(EXAMS)
    before = len(agent.messages)
    agent(
        "Start a new S3 practice exam with exactly two questions using "
        "start_practice_exam. Show the first question and wait for my answer. "
        "Do not answer questions for me or reveal the correct answers."
    )
    sessions = set(EXAMS) - existing_sessions
    require(len(sessions) == 1, "Expected exactly one new exam session")
    session_id = sessions.pop()

    try:
        exam = EXAMS[session_id]
        require(len(exam["questions"]) == 2, "Expected a two-question exam")
        require(not exam["answers"], "Agent answered before the student")
        require("start_practice_exam" in tool_calls(agent, before),
                "Agent did not start the exam through the tool")

        for index, question in enumerate(exam["questions"]):
            # One correct and one wrong answer exercise grading in both directions.
            answer = question["answer"] if index == 0 else next(
                option for option in question["options"]
                if option != question["answer"]
            )
            before = len(agent.messages)
            agent(
                f"My answer is {answer}. Use submit_exam_answer to save it "
                "for the current question. Show the next question if there "
                "is one. Do not finish or grade the exam until I ask."
            )
            require("submit_exam_answer" in tool_calls(agent, before),
                    "Agent did not submit the student's answer")
            require(exam["answers"].get(question["id"]) == answer,
                    "Wrong question or answer saved")
            require(len(exam["answers"]) == index + 1,
                    "Agent submitted extra answers")
            require(not exam["finished"], "Agent finished before being asked")

        before = len(agent.messages)
        agent("Finish my exam using finish_practice_exam and show my score.")
        require("finish_practice_exam" in tool_calls(agent, before),
                "Agent did not finish the exam through the tool")
        require(exam["finished"], "Exam was not completed")

        summary = progress.get_progress_summary()
        require(summary["total_exams"] == 1, "Expected one saved exam")
        require(summary["correct_answers"] == 1, "Expected one correct answer")
        require(summary["total_questions"] == 2, "Expected two graded questions")
        require(summary["overall_accuracy"] == 50.0, "Incorrect exam grading")
        require(summary["passed_exams"] == 0, "A 50% exam should not pass")

        before = len(agent.messages)
        agent("Show my saved student progress using get_student_progress.")
        require("get_student_progress" in tool_calls(agent, before),
                "Agent did not retrieve saved progress")
        print("PASS: two-question exam, grading, and saved student progress")
    finally:
        for created_session in set(EXAMS) - existing_sessions:
            EXAMS.pop(created_session, None)


def check_labs(agent):
    before = len(agent.messages)
    agent(
        "Give me the three hands-on labs. Call generate_lab_task for S3, "
        "generate_lambda_lab_task, and generate_iam_lab_task. Call all three, "
        "then return only each lab's title. Do not create any AWS resources."
    )
    expected = {
        "generate_lab_task": "s3-secure-bucket",
        "generate_lambda_lab_task": "lambda-basic-config",
        "generate_iam_lab_task": "iam-least-privilege",
    }
    outputs = tool_outputs(agent, before)
    for name, lab_id in expected.items():
        require(outputs.get(name, {}).get("lab_id") == lab_id,
                f"Missing or wrong lab returned by {name}")
    print("PASS: S3, Lambda, and IAM lab generation")

    # Keep this smoke test independent of real student resources and permissions.
    with patch.dict(os.environ, {"AWS_STUDY_ACCOUNT_ID": ""}):
        before = len(agent.messages)
        agent(
            "Now call all three read-only verification tools: verify_lab_task "
            "with bucket_name study-coach-lab-smoke, verify_lambda_lab_task "
            "with function_name study-coach-lab-smoke, and verify_iam_lab_task "
            "with role_name study-coach-lab-s3-reader. Even if one reports a "
            "configuration error, call the other two and summarize the errors. "
            "Do not create or change any resources."
        )
    outputs = tool_outputs(agent, before)
    for name in ("verify_lab_task", "verify_lambda_lab_task", "verify_iam_lab_task"):
        require(outputs.get(name, {}).get("error") ==
                "AWS_STUDY_ACCOUNT_ID is not configured",
                f"Expected a missing-account configuration error from {name}")
        require("score" not in outputs[name],
                "Missing configuration must not be reported as a graded lab")
    print("PASS: all lab verifiers report missing account configuration")


def main():
    parser = argparse.ArgumentParser(
        description="Live Bedrock checks; requires AWS credentials and incurs inference costs."
    )
    parser.add_argument(
        "--scenario", choices=("study", "exam", "labs", "all"), default="study"
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="study-coach-smoke-") as directory:
        with patch.object(progress, "PROGRESS_FILE", Path(directory) / "progress.json"):
            try:
                if args.scenario in ("study", "all"):
                    agent = _get_agent(str(uuid4()), "smoke-test-user")
                    check_study_materials(agent)
                if args.scenario in ("exam", "all"):
                    agent = _get_agent(str(uuid4()), "smoke-test-user")
                    check_exam(agent)
                if args.scenario in ("labs", "all"):
                    agent = _get_agent(str(uuid4()), "smoke-test-user")
                    check_labs(agent)
            finally:
                _get_agent.cache_clear()



if __name__ == "__main__":
    main()
