# Study Coach agent

> The cloud deployment is intentionally paused. Source code is preserved; restore the deployment before using a cloud runtime ARN. See the [pause and restore record](../../security/iam-deployment-status.md).

The deployed Python application uses Strands, Amazon Bedrock, and AgentCore Runtime. See the [project README](../../README.md) for the verified deployment, terminal client, and tests.

## Files and state

- main.py registers the study, exam, progress, and lab tools.
- model/load.py creates the Claude Haiku 4.5 Bedrock model.
- exam_mode.py keeps active exams in process memory.
- progress.py selects local JSON or durable S3 completed-exam storage.
- progress_s3.py writes conditional, per-exam S3 objects.
- data/questions.json contains the predefined question bank.

AgentCore Memory is not provisioned. The helper in memory/session.py is not attached to the agent. Conversation history lives in cached agent instances within the running process.

## Payload

The runtime accepts a JSON object with prompt (a string) or messages (caller-supplied history). messages takes precedence. parse.py validates the payload and normalizes trailing toolUse blocks in history.

Optional actorId defaults to default. It is part of the cached agent key, not authenticated identity, and does not isolate progress. This deployment is for a single authorized user.

The runtime session ID comes from AgentCore request context, not the payload. Reuse a session to continue a conversation.

~~~json
{"prompt":"Start a two-question S3 practice exam","actorId":"demo-user"}
~~~

Use app/chat.py from the repository root for interactive cloud access.

## Environment

| Variable | Use |
| --- | --- |
| AWS_REGION | Bedrock region; defaults to eu-central-1 |
| BEDROCK_MODEL_ID | Defaults to the Claude Haiku 4.5 EU inference profile |
| AWS_PROFILE | Local credentials profile; AWS uses the runtime role |
| AWS_STUDY_ACCOUNT_ID | Expected lab account; configured by CDK in AWS |
| PROGRESS_S3_BUCKET | Durable completed-exam store; configured by CDK in AWS |

Without PROGRESS_S3_BUCKET, progress uses data/student_progress.json. Local smoke tests disable the S3 backend and patch a temporary file. Cloud smoke tests verify S3 persistence and remove only their own record version.

Completed cloud results survive runtime restarts. Active exams and conversations do not. Finish an exam before closing its session.

## Build

Install from the repository root using uv sync --locked --project app/agent --python 3.12.

CDK stages only reviewed runtime files and applies exact lockfile dependencies to the staged manifest. Local progress and environment files are excluded.

See the [current deployment state](../../security/iam-deployment-status.md) before changing AWS resources.
