"""Opt-in deployed-runtime test. Writes one exam, checks it, then removes its exact S3 version."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.config import Config


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def invoke(client, arn, session, prompt):
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn, runtimeSessionId=session,
        payload=json.dumps({"prompt": prompt}).encode(),
    )
    require("text/event-stream" in response.get("contentType", ""), "Expected SSE response")
    calls, active, text = [], {}, []
    with response["response"] as body:
        # SDK versions return either StreamingBody or urllib3 HTTPResponse.
        # Both support read(); only StreamingBody exposes iter_lines().
        for raw in body.read().splitlines():
            line = raw.decode("utf-8")
            if not line.startswith("data:"):
                continue
            value = json.loads(line[5:].strip())
            if isinstance(value, str):
                value = json.loads(value)
            require("error" not in value, f"Runtime error: {value}")
            event = value.get("event", value)
            require(not any(key.endswith("Exception") for key in event), f"Stream error: {event}")
            start = event.get("contentBlockStart", {})
            tool = start.get("start", {}).get("toolUse")
            if tool:
                active[start["contentBlockIndex"]] = {"name": tool["name"], "raw": ""}
            block = event.get("contentBlockDelta", {})
            delta = block.get("delta", {})
            if "text" in delta:
                text.append(delta["text"])
            if "toolUse" in delta:
                active[block["contentBlockIndex"]]["raw"] += delta["toolUse"].get("input", "")
            stop = event.get("contentBlockStop", {})
            index = stop.get("contentBlockIndex")
            if index in active:
                call = active.pop(index)
                calls.append({"name": call["name"], "input": json.loads(call["raw"] or "{}")})
    answer = "".join(text)
    require("<thinking>" not in answer, "Internal thinking tags appeared in visible output")
    return calls, answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--progress-bucket", required=True)
    args = parser.parse_args()
    region = args.runtime_arn.split(":")[3]
    client = boto3.client("bedrock-agentcore", region_name=region,
                          config=Config(read_timeout=300, retries={"max_attempts": 0}))
    s3 = boto3.client("s3", region_name=region)
    sessions = [str(uuid4()), str(uuid4())]
    active_sessions = {sessions[0]}
    record_key = version = None
    try:
        calls, answer = invoke(client, args.runtime_arn, sessions[0],
            "Run this smoke exam using the tools: start_practice_exam(topic='S3', count=1), "
            "then submit_exam_answer with my answer A for that question, then "
            "finish_practice_exam. Do not start another exam. Show the final score.")
        names = [call["name"] for call in calls]
        require(all(name in names for name in ("start_practice_exam", "submit_exam_answer", "finish_practice_exam")),
                f"Missing exam tools: {names}; answer: {answer}")
        finished = [call for call in calls if call["name"] == "finish_practice_exam"]
        require(len(finished) == 1, "Expected one finished exam")
        exam_id = finished[0]["input"]["session_id"]
        record_key = "progress/exams/" + hashlib.sha256(exam_id.encode()).hexdigest() + ".json"
        response = s3.get_object(Bucket=args.progress_bucket, Key=record_key)
        version = response["VersionId"]
        with response["Body"] as body:
            record = json.loads(body.read())
        bank = json.loads((Path(__file__).resolve().parents[1] / "app/agent/data/questions.json").read_text())
        questions = {question["id"]: question for question in bank}
        require(record["session_id"] == exam_id and record["total"] == 1, "Wrong persisted exam")
        result = record["results"][0]
        require(result["selected_answer"] == "A", "Wrong student answer persisted")
        expected = int(questions[result["question_id"]]["answer"] == "A")
        require(record["score"] == expected and record["percentage"] == expected * 100,
                "Persisted score does not match the question bank")
        print("PASS: deployed Claude exam tools and independently verified S3 grading", flush=True)

        client.stop_runtime_session(agentRuntimeArn=args.runtime_arn, runtimeSessionId=sessions[0])
        active_sessions.remove(sessions[0])
        active_sessions.add(sessions[1])
        calls, answer = invoke(client, args.runtime_arn, sessions[1],
            "Use get_student_progress to load my completed exams from storage. "
            "Return only JSON with a numeric total_exams field. Do not start a new exam.")
        require(any(call["name"] == "get_student_progress" for call in calls), "Progress tool was not called in the new runtime session")
        # The saved object must remain after the old runtime session is stopped.
        s3.head_object(Bucket=args.progress_bucket, Key=record_key, VersionId=version)
        count = sum(len(page.get("Contents", [])) for page in
                    s3.get_paginator("list_objects_v2").paginate(Bucket=args.progress_bucket, Prefix="progress/exams/"))
        reported = json.loads(answer[answer.find("{"):answer.rfind("}") + 1])
        require(reported.get("total_exams") == count, f"Progress count mismatch: {answer}")
        print("PASS: progress retrieval in a fresh runtime session after stopping the first", flush=True)

        account = args.runtime_arn.split(":")[4]
        calls, answer = invoke(client, args.runtime_arn, sessions[1],
            f"Verify existing labs using verify_lab_task('study-coach-lab-{account}-euc1'), "
            "verify_lambda_lab_task('study-coach-lab-basic-lambda'), and "
            "verify_iam_lab_task('study-coach-lab-s3-reader'). Call all three. "
            "Return only a JSON object with numeric scores: s3, lambda, iam.")
        names = {call["name"] for call in calls}
        require({"verify_lab_task", "verify_lambda_lab_task", "verify_iam_lab_task"} <= names,
                f"Missing lab verification tools: {names}")
        start, end = answer.find("{"), answer.rfind("}")
        scores = json.loads(answer[start:end + 1])
        require(scores == {"s3": 3, "lambda": 5, "iam": 5}, f"Cloud labs did not pass: {scores}")
        print("PASS: deployed runtime lab checks: S3 3/3, Lambda 5/5, IAM 5/5", flush=True)
    finally:
        if record_key and version:
            s3.delete_object(Bucket=args.progress_bucket, Key=record_key, VersionId=version)
            print("Removed only the generated smoke-exam object version", flush=True)
        for session in active_sessions:
            client.stop_runtime_session(agentRuntimeArn=args.runtime_arn, runtimeSessionId=session)


if __name__ == "__main__":
    main()
