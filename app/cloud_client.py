"""Shared SSE response reader for the demo client and cloud smoke test."""

import json


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

