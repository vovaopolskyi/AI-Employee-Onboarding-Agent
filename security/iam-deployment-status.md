# AWS Study Coach deployment status

## Cloud pause

The cloud deployment was intentionally removed on 2026-11-21 at the owner's request to avoid continued project usage. The release code and its successful validation history remain in Git. Live test and chat commands must wait until the deployment is restored.

Final teardown audit confirmed:

- CloudFormation stack: DELETE_COMPLETE.
- Project AgentCore runtimes and endpoints: removed.
- Designated lab Lambda: removed.
- Lab and progress S3 buckets: removed after checking/backing up data.
- Runtime and lab Lambda log groups: absent.
- Four backed-up project artifact versions: removed from the shared CDK assets bucket.
- Shared assets bucket: zero objects/versions, delete markers, or multipart uploads.

The shared CDK bootstrap and IAM configuration were preserved. The final audit snapshot is in agentcore/.cache/pause-backup/teardown-verification.json.

Local restore material is kept in ignored agentcore/.cache/pause-backup/: the cloud-state snapshot, runtime logs, the current and previous CodeZip files, the lab Lambda ZIP, lab bucket configuration, and progress-0.json containing the completed exam present before teardown. These backups are not uploaded to GitHub.

The scoped execution policy includes teardown of this exact runtime, its endpoint, workload identity, and runtime role. AgentCore workload-identity deletion needs authorization for both the identity and its parent directory; see the [service authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_bedrock-agentcore.html). These permissions do not grant IAM administration over other project roles.

To restore later:

1. Refresh the AWS sign-in and review the saved configuration and source templates.
2. Recreate the designated lab resources, using the saved Lambda ZIP/configuration if needed.
3. Review the scoped CloudFormation creation permissions: the policy records historical physical runtime/role ARNs, and a fresh deployment can receive new IDs.
4. Build the locked CodeZip, refresh the approved artifact allowlist, and create a reviewed deployment.
5. Restore saved progress into the recreated private progress bucket and update the chat client's runtime ARN.

GitHub Actions remains offline and does not automatically recreate AWS resources. Previous AWS usage charges are not undone by teardown.

## Last verified single-user cloud demo before pause

Verified on 2026-11-21:

- CloudFormation AgentCore-AWSStudyCoach-default: **UPDATE_COMPLETE**.
- AgentCore Runtime AWSStudyCoach_default_agent-ftNEInBBU3: **READY**, version **3**, in eu-central-1.
- Model: eu.anthropic.claude-haiku-4-5-20251001-v1:0.
- Runtime boundary AWSStudyCoachRuntimeBoundary: active version **v3**.
- Stack execution role: StudyCoachCloudFormationExecutionRole.
- Progress bucket: study-coach-progress-054776129200-eu-central-1-an.
- Normal terminal access through app/chat.py succeeded and reported zero exams after smoke cleanup.

This is a single-user learning demo accessed through IAM-authorized AgentCore calls, not a multi-user production service.

## Verification evidence

- 62 Python unit tests passed.
- CDK compilation, source staging, and dependency-lock checks passed.
- All 113 installed package versions in the release ZIP matched uv.lock.
- ZIP inspection excluded student_progress.json and environment files and retained the question bank.
- Local Claude study, exam/progress, lab-generation, and real-resource checks passed.
- The deployed smoke test independently compared an exam's saved S3 score with the question bank.
- After stopping the original runtime session, a fresh session read completed progress from S3.
- Deployed lab checks passed: S3 3/3, Lambda 5/5, IAM 5/5.
- Generated smoke object versions, including the interrupted initial attempt's record, were removed. No user history existed in the new bucket at cleanup.
- Ordinary terminal progress retrieval subsequently reported zero exams.

## Controls of the last verified deployment

The runtime identity policy and boundary restricted inference to the approved Claude profile and its six EU destinations. Lab reads were scoped to the designated S3 bucket, Lambda function, and IAM role. Progress access permitted list/read/write only under progress/exams/; the runtime had no progress-delete permission. The runtime role has now been removed; the boundary configuration is retained.

The progress bucket had versioning, SSE-S3, blocked SSE-C, all four Block Public Access settings, BucketOwnerEnforced ownership, ABAC, and an HTTPS-only policy. CloudFormation retained it during stack deletion; explicit cleanup removed its backed-up exam version and then the bucket. No additional access-log bucket or data-event trail was requested.

The scoped CloudFormation role permits existing runtime/role updates, management of this progress bucket, reading the exact bootstrap SSM parameter, and read/decrypt access to the approved new/rollback CodeZip objects. KMS access is constrained to the assets key through S3 and the assets encryption context.

CDK explicitly selects the scoped execution role. Its deployment action role has the corresponding project-specific pass-role grant for CloudFormation.

Policy sources:

- [Execution policy](cloudformation-execution-policy.json).
- [Active boundary document](runtime-boundary-claude.draft.json), whose legacy filename predates activation.
- [Generated action baseline](runtime-actions.generated.json); CDK narrows optional actions and resource scope.
- [CDK pass-role grant](cdk-deployment-passrole.json).

## Release and recovery record

The first change-set request exposed missing SSM bootstrap-parameter access. The first runtime update then exposed missing CodeZip access for the restricted deployment caller. Resource-specific S3 and KMS permissions corrected that dependency.

Rollback completed successfully. The new bucket had been retained, so it was imported back into the same stack. The final update changed the runtime in place and completed successfully.

Boundary v2 was transitional; v3 is final. Earlier versions and the prior code artifact remain as recovery material. The pre-deployment template/policy backup is kept locally in ignored agentcore/.cache/deployment-backup.json.

AgentCore CLI 1.0.2 was used. Its build command is agentcore build; it does not expose validate, deploy --dry-run, or deploy --diff. Review installed CLI flags and the real change set for another release.

Refresh the explicit new/rollback ZIP allowlist for future artifacts. A local build does not update AWS.

## Scope limits

When deployed, completed results are durable and active exams remain process-local. During this pause, the saved exam is in the local backup rather than cloud storage. Multi-user authentication/data isolation, a web interface, and extra labs are later extensions. Shared S3 history is for the single-user demo, not high-volume analytics.
