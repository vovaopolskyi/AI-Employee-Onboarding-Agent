AWS Study Coach agent, built with Strands and Amazon Bedrock AgentCore. See the [project README](../../README.md) for features, AWS profiles, test commands, and deployment status.

# Layout

The generated application code lives at the agent root directory. At the root, there is a `.gitignore` file, an
`agentcore/` folder which represents the configurations and state associated with this project. Other `agentcore`
commands like `deploy`, `dev`, and `invoke` rely on the configuration stored here.

## Agent Root

The main entrypoint to your app is defined in `main.py`. Using the AgentCore SDK `@app.entrypoint` decorator, this
file defines a Starlette ASGI app with the Strands Agent SDK running within.

`model/load.py` instantiates the chosen model provider.

## Memory

AgentCore Memory is not provisioned: `agentcore/agentcore.json` has an empty `memories` list,
and `main.py` does not attach the helper in `memory/session.py` to the agent.
Conversation history is kept in cached agent instances in process memory. Exams also use
process memory; student progress uses a single local JSON file. Restarting the server loses
conversations and active exams. These stores do not provide authenticated user isolation.

## Input Validation

Validate invocation input before forwarding it to Strands. Keep plain prompts typed as strings. If the app accepts a
caller-supplied message history, retain `_strip_trailing_tool_use()` in `parse.py`, which normalizes the history tail
before invoking the agent.

## Payload

The Runtime accepts a JSON object. `parse_payload()` reads:

- `prompt` (string) — a single user message. Used when `messages` is absent; defaults to `""`.
- `messages` (array) — a full conversation history (`[{"role": ..., "content": [...]}]`). Takes precedence over `prompt`; trailing `toolUse` blocks are stripped before the agent runs.
- `actorId` (string, optional) — part of the in-process agent cache key. Defaults to `"default"`. This caller-supplied value is not authenticated identity and does not isolate student progress.

Provide either `prompt` or `messages`. The `session_id` is not in the body — it comes from the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header (`context.session_id`); reuse it to continue a conversation.

```json
{ "prompt": "Start a two-question S3 practice exam", "actorId": "user-123" }
```

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `AWS_REGION` | No | Bedrock region, defaults to `eu-central-1` |
| `BEDROCK_MODEL_ID` | No | Defaults to the Claude Haiku 4.5 EU inference profile |
| `AWS_PROFILE` | No | Local AWS credentials profile; use the execution role in AWS |
| `AWS_STUDY_ACCOUNT_ID` | For lab checks | Expected 12-digit AWS account ID |

# Developing locally

If installation was successful, a virtual environment is already created with dependencies installed.

Activate the environment with `source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate.bat` in Windows
Command Prompt, or `.\.venv\Scripts\activate.ps1` in Windows PowerShell.

`agentcore dev` will start a local server on 0.0.0.0:8080.

# Deployment

Before deployment, review the [project deployment status](../../README.md#security-and-deployment-status)
and [IAM transition checklist](../../security/iam-deployment-status.md). The expanded agent has
not yet been validated in the deployed runtime. Review the CodeZip artifact, runtime permissions,
permissions boundary, and CloudFormation execution role before updating AWS resources.

Invoke the deployed Runtime with its native payload:

```bash
agentcore invoke --runtime agent --payload '{"prompt":"Hello!"}'
```
