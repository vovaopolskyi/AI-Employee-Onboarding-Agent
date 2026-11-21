# AWS AI Certification Study Coach

A Python study assistant using Strands Agents, Claude Haiku 4.5 on Amazon Bedrock, and Amazon Bedrock AgentCore.

> **Cloud status: intentionally paused; cloud resources removed on 2026-11-21.** The runtime, lab Lambda, both project buckets, runtime logs, and project-owned S3 artifacts have been deleted. Code and the verified release remain in Git. Local backups are in agentcore/.cache/pause-backup/ (excluded from Git). Restore the deployment before using cloud chat or live tests.

The completed exam present before teardown was backed up as progress-0.json. The CloudFormation stack reached DELETE_COMPLETE. Shared CDK bootstrap infrastructure and IAM configuration were preserved; its assets bucket was verified empty, including versions and multipart uploads. Offline CI does not recreate cloud resources. Previous AWS usage charges remain payable.

**The single-user learning demo was deployed and verified in AWS before pausing it.** Cloud tests completed an exam, checked the saved score independently, loaded progress from a fresh runtime session, and passed the three real lab verifiers.

## Features

- 50 predefined questions across S3, IAM, Lambda, EC2, and VPC, with topic and difficulty filtering.
- Answer checking with explanations.
- Practice exams of 1-20 questions, limited by the selected topic's available questions.
- Curated official AWS documentation search for S3, IAM, and Lambda.
- Read-only configuration checks for S3, Lambda, and IAM labs.
- Completed-exam history and topic statistics that survive runtime restarts.

The practice passing threshold is **70%**, a project rule rather than an official AWS Certification passing score.

## Last verified deployment before pause

| Component | Last verified state |
| --- | --- |
| Region | eu-central-1 |
| CloudFormation | AgentCore-AWSStudyCoach-default - UPDATE_COMPLETE |
| Runtime | AWSStudyCoach_default_agent-ftNEInBBU3 - READY, version 3 |
| Model | eu.anthropic.claude-haiku-4-5-20251001-v1:0 |
| Runtime boundary | AWSStudyCoachRuntimeBoundary - active version v3 |
| Stack execution role | StudyCoachCloudFormationExecutionRole |
| Progress bucket | study-coach-progress-054776129200-eu-central-1-an |

The model uses an EU cross-region inference profile. The runtime uses its own IAM role, not developer SSO credentials.

## Run after restoring the cloud deployment

Requires Python 3.12, uv, and AWS credentials authorized to invoke and stop this runtime. From the repository root in Windows PowerShell:

~~~powershell
uv sync --locked --project app/agent --python 3.12
$env:AWS_PROFILE = "study-coach-sso"
$env:AWS_REGION = "eu-central-1"
$env:AWS_DEFAULT_REGION = "eu-central-1"
$runtimeArn = "<runtime-arn-from-the-restored-deployment>"

& ./app/agent/.venv/Scripts/python.exe app/chat.py --runtime-arn $runtimeArn
~~~

If your established SSO session has expired, refresh it through your usual IAM Identity Center sign-in workflow.

Example prompts:

- "Find official AWS S3 study materials."
- "Start a two-question S3 practice exam."
- Answer each question with A, B, C, or D, then ask to finish the exam.
- "Show my progress."
- "Verify my S3, Lambda, and IAM labs."

Type **/quit** to close the runtime session. Finish an exam before exiting: completed results persist, while unfinished exams live only in memory.

For one request:

~~~powershell
& ./app/agent/.venv/Scripts/python.exe app/chat.py --runtime-arn $runtimeArn --prompt "Show my progress"
~~~

The terminal client uses boto3 directly, avoiding PowerShell/native CLI JSON-quoting differences. Ordinary cloud chat needs runtime invocation/session-stop permissions; the runtime supplies Bedrock, progress-storage, and lab access. Bedrock, AgentCore Runtime, and S3 usage incur AWS charges.

## Storage and scope

Local development uses app/agent/data/student_progress.json, excluded from Git. PROGRESS_S3_BUCKET selects the cloud backend.

The cloud backend stores one JSON object per completed exam under progress/exams/. Conditional writes prevent duplicates; separate objects avoid concurrent read-modify-write data loss. History is sorted by completion time. S3 errors are surfaced rather than silently falling back to temporary local storage.

This is a **single-user demo** accessed through AWS IAM. actorId is caller-supplied context, not authenticated end-user identity. There are no multi-user accounts or private per-student histories. Active exams and conversation history disappear when their runtime session ends.

## Hands-on labs

Students create lab resources themselves. The tools only read their configurations.

| Lab | Deployed result | Designated resource |
| --- | --- | --- |
| S3 secure bucket | 3/3 | study-coach-lab-<account-id>-euc1 |
| Lambda configuration | 5/5 | study-coach-lab-basic-lambda |
| IAM least privilege | 5/5 | study-coach-lab-s3-reader |

S3 checks versioning, all four Block Public Access settings, SSE-S3 encryption, owner, and region. Lambda checks the prescribed runtime, memory, timeout, state, and role account. IAM checks the prescribed trust and inline policy configuration; it does not calculate complete effective permissions.

Runtime access is scoped to these designated resources. Clean up student-created resources when no longer needed.

## Validation

**62 Python unit tests passed.** CDK compilation and source-staging/lockfile regression checks passed. GitHub Actions runs these offline checks on pushes and pull requests.

~~~powershell
& ./app/agent/.venv/Scripts/python.exe -m unittest discover -s test -p "test_*.py" -v
npm.cmd --prefix agentcore/cdk test
~~~

The live checks below require restored resources and incur AWS usage charges. Do not run them while paused. The offline unit tests above can still be used.

Opt-in local agent checks call Bedrock but use temporary progress storage:

~~~powershell
& ./app/agent/.venv/Scripts/python.exe test/smoke_study_agent.py --scenario all
& ./app/agent/.venv/Scripts/python.exe test/smoke_study_agent.py --scenario real-labs --account-id "054776129200" --lab-bucket "study-coach-lab-054776129200-euc1" --lab-function "study-coach-lab-basic-lambda"
~~~

The deployed-runtime check also passed:

~~~powershell
& ./app/agent/.venv/Scripts/python.exe test/smoke_cloud_runtime.py --runtime-arn $runtimeArn --progress-bucket "study-coach-progress-054776129200-eu-central-1-an"
~~~

It verifies actual tool calls, compares the saved score with the question bank, stops the first session, checks progress in a fresh session, and verifies all three labs. It removes only its generated exam object's exact version and closes its sessions. Its caller needs additional S3 read/list/delete-version permissions; the runtime itself has no progress-delete permission.

Smoke records were cleaned up after validation. A later completed user exam was preserved in the local pause backup before removing the cloud store. The test_exam_manual.py driver is optional local development material.

## Architecture

~~~text
Terminal / IAM-authorized caller
              |
       AgentCore Runtime
              |
        Strands Agent
         /    |    \
        v     v     v
     Bedrock Study Read-only lab APIs
     Claude  tools   S3 / Lambda / IAM
              |
        Exam completion
              |
       Private S3 progress bucket
~~~

Sources: [agent](app/agent/main.py), [questions](app/agent/data/questions.json), [exams](app/agent/exam_mode.py), [progress](app/agent/progress.py), [S3 backend](app/agent/progress_s3.py), and [CDK stack](agentcore/cdk/lib/cdk-stack.ts).

## Local development and releases

After configuring Bedrock credentials, start a local server:

~~~powershell
Set-Location app/agent
& ./.venv/Scripts/python.exe main.py
~~~

Local lab checks also need AWS_STUDY_ACCOUNT_ID and the corresponding read-only permissions. See [agent payload and environment details](app/agent/README.md).

CodeZip stages only the reviewed files in [runtime-source.ts](agentcore/cdk/lib/runtime-source.ts), excluding progress, environment files, and unlisted data. Add new runtime modules/data to that list.

The build exports exact dependencies from uv.lock into the staged manifest. All **113 installed package versions** in the release ZIP matched the lockfile. Invalid or stale locks fail the build.

~~~powershell
agentcore build
~~~

Before another deployment, review the template/ZIP, refresh the execution role's explicit new/rollback artifact allowlist, and use the scoped CloudFormation role. CDK now selects that role, and the deployment action role has a project-specific pass-role grant.

The progress bucket uses the account-regional namespace, versioning, SSE-S3, blocked SSE-C, Block Public Access, disabled ACLs, ABAC, and an HTTPS-only policy. It is retained on stack deletion; remove it separately only when its data is no longer needed. No additional access-log bucket or CloudTrail data-event trail was requested.

See [deployment state and recovery notes](security/iam-deployment-status.md) for applied policies and release details.

## Optional extensions

Multi-user authentication and data isolation, durable active exams, a browser interface, and more EC2/VPC labs are outside the completed single-user learning-demo scope.
