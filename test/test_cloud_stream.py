import io
import json
import unittest
from unittest.mock import MagicMock

from smoke_cloud_runtime import invoke


class Body(io.BytesIO):
    def iter_lines(self):
        return self.getvalue().splitlines()


class CloudStreamTests(unittest.TestCase):
    def test_reassembles_tool_arguments_and_only_visible_text(self):
        events = [
            {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"name": "finish_practice_exam", "toolUseId": "id"}}}},
            {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": '{"session_id":'}}}},
            {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": '"exam"}'}}}},
            {"contentBlockStop": {"contentBlockIndex": 0}},
            {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {"reasoningContent": {"text": "private reasoning"}}}},
            {"contentBlockDelta": {"contentBlockIndex": 2, "delta": {"text": "Score: 1/1"}}},
        ]
        data = b"\n".join(b"data: " + json.dumps({"event": event}).encode() for event in events)
        client = MagicMock()
        body = Body(data)
        client.invoke_agent_runtime.return_value = {"contentType": "text/event-stream", "response": body}
        calls, answer = invoke(client, "runtime-arn", "session", "prompt")
        self.assertEqual(calls, [{"name": "finish_practice_exam", "input": {"session_id": "exam"}}])
        self.assertEqual(answer, "Score: 1/1")
        self.assertTrue(body.closed)

    def test_runtime_error_is_not_accepted_as_an_empty_success(self):
        client = MagicMock()
        client.invoke_agent_runtime.return_value = {"contentType": "text/event-stream", "response": Body(b'data: {"error":"failed"}')}
        with self.assertRaisesRegex(AssertionError, "Runtime error"):
            invoke(client, "runtime-arn", "session", "prompt")


if __name__ == "__main__":
    unittest.main()
