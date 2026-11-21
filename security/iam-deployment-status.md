# AWS Study Coach IAM deployment status

## Previously verified
- Claude Haiku 4.5 Runtime identity policy is defined in CDK.
- Runtime permissions boundary is attached.
- Non-Bedrock IAM statements match deployed permissions.
- IAM Simulator allows Claude and denies Nova.
- Scoped CloudFormation execution policy is applied and validated.
- CodeZip and 53 automated tests passed.

## Pending deployment
- CloudFormation stack still uses the CDK bootstrap execution role with AdministratorAccess.
- StudyCoachCloudFormationExecutionRole is not yet assigned to the stack.
- AWSStudyCoachRuntimeBoundary v1 is still active.
- Claude-only boundary draft has not been activated.
- Cloud deployment and smoke tests remain pending.

## Planned sequence
1. Verify the scoped CloudFormation role is sufficient for update and rollback.
2. Review the final CloudFormation changes and execution-role transition.
3. Deploy Claude Runtime and verify functionality.
4. Activate the Claude-only boundary as a new managed-policy version.
5. Repeat smoke tests and validate effective IAM permissions.

Do not treat this PR as evidence that the cloud deployment is complete.

## Preflight review: 2026-11-21

Read-only AWS inspection confirmed:

- The CloudFormation stack is `UPDATE_COMPLETE` and still references the CDK bootstrap execution role.
- AgentCore Runtime is `READY`, version `1`, with its code last updated on 2026-11-12.
- The deployed runtime has no `AWS_STUDY_ACCOUNT_ID` environment variable.
- The deployed identity policy still allows broad Bedrock model/profile invocation; it is not the Claude-only policy in the repository.
- The runtime boundary is still version `v1`. Neither the inspected inline policy nor that boundary includes the lab verifier actions.

Local validation now includes actual Claude tool calls against existing S3, Lambda, and IAM labs: 3/3, 5/5, and 5/5. This used `study-coach-sso`, not the runtime role, and does not establish the runtime's effective permissions.

### Build findings

- AgentCore CLI `1.0.2` supports `agentcore build`. It does not expose `validate`, `deploy --dry-run`, or `deploy --diff`; check `--help` before following commands from a different CLI version.
- A fresh CodeZip build succeeded, but originally included local `data/student_progress.json`. The source-staging fix on `fix/codezip-source` excludes unlisted files. Its regression test and rebuilt ZIP inspection passed: progress and `.env` files were absent; the entrypoint and question bank were present. Merge that fix before building a deployment artifact.
- The ZIP contained `strands-agents 1.64.0` and `bedrock-agentcore 1.26.1` during inspection. The installed packager uses `uv pip install -r pyproject.toml`, not a locked `uv sync`; pinning Strands alone does not make every dependency reproducible. Review dependency resolution before declaring CodeZip drift resolved.

### Remaining work before deployment

1. Add scoped lab-read permissions to both the runtime identity policy and the permissions boundary. Verify allowed lab access and denied access to unrelated resources; the current Claude-only boundary draft also lacks lab permissions.
2. Configure the expected account ID for the runtime. Verify the Bedrock model and region configuration in the synthesized template.
3. Address progress storage for the intended deployment: local JSON is not durable cloud storage, and the in-memory exam store is not a multi-user backend.
4. Verify update and rollback permissions for the dedicated CloudFormation execution role before assigning it to the stack.
5. Build a clean artifact after the relevant PRs are merged, inspect the final template and ZIP, then deploy and repeat smoke tests using the runtime identity.

### Reproduce the lab policy baseline

IAM Policy Autopilot `0.4.0` identified these read-only actions from the application: `s3:ListBucket`, `s3:GetBucketVersioning`, `s3:GetBucketPublicAccessBlock`, `s3:GetEncryptionConfiguration`, `lambda:GetFunctionConfiguration`, `iam:GetRole`, `iam:GetRolePolicy`, `iam:ListRolePolicies`, and `iam:ListAttachedRolePolicies`.

From the repository root, replace the account placeholder with the expected account:

```powershell
uvx iam-policy-autopilot@0.4.0 generate-policies "$PWD/app/agent/practice.py" "$PWD/app/agent/lambda_lab.py" "$PWD/app/agent/iam_lab.py" --region eu-central-1 --account "<12-digit-account-id>" --service-hints s3 lambda iam --pretty
```

This produces a baseline without uploading a policy. Its resource patterns are broad because the code accepts resource names at runtime; scope them to the designated lab resources before attaching anything. No runtime policy, boundary version, or CloudFormation execution role was changed during this preflight review.
