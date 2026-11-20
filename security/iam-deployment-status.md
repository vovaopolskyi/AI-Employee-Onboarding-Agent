# AWS Study Coach IAM deployment status

## Verified
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
