# AWS AI Certification Study Coach Agent

An AI-powered AWS Certification Study Coach built with Python, Strands Agents SDK, Amazon Bedrock, and Amazon Bedrock AgentCore.

## Project Overview

This project demonstrates practical AI agent development using AWS generative AI services, infrastructure as code, observability, and IAM security controls.

The goal is to build an intelligent study assistant capable of explaining AWS concepts, retrieving curated study materials, and supporting interactive certification practice.

The current implementation is a working cloud-deployed prototype. Certification-specific study tools are planned for future development.

## Technology Stack

- Python 3.12
- Strands Agents SDK
- Amazon Bedrock (Amazon Nova Micro)
- Amazon Bedrock AgentCore Runtime
- AWS CDK and AWS CloudFormation
- AWS IAM and IAM Identity Center
- Amazon CloudWatch
- Git and GitHub

## Current Progress

- [x] Initialize the AgentCore project
- [x] Configure a Strands agent with Amazon Bedrock
- [x] Run the agent locally
- [x] Implement and verify the `add_numbers` Python tool
- [x] Deploy the agent to AgentCore Runtime in `eu-central-1`
- [x] Verify cloud agent invocation and tool execution
- [x] Inspect runtime logs in Amazon CloudWatch
- [x] Add resource tagging to the CDK configuration
- [x] Document the least-privilege deployment design
- [x] Create an IAM permissions boundary for the Runtime execution role
- [x] Apply the permissions boundary to the deployed execution role
- [x] Verify successful agent invocation after applying the boundary
- [x] Create a dedicated CloudFormation execution role with scoped initial permissions
- [x] Prepare a boundary-only CloudFormation change set for review
- [ ] Execute and verify the boundary-only CloudFormation change set
- [ ] Complete and validate the least-privilege CloudFormation deployment workflow
- [ ] Implement the study materials search tool
- [ ] Implement the practice question tool
- [ ] Add automated tests
- [ ] Complete deployment, cost, and cleanup documentation

## Current Architecture

### Local Development

```text
Local Client
     |
AgentCore Development Server
     |
 Strands Agent
     |
 Amazon Bedrock
 (Nova Micro)
```

### AWS Cloud Deployment

```text
Amazon Bedrock AgentCore Runtime
          (eu-central-1)
                 |
           Strands Agent
             /       \
    Amazon Bedrock   Python Tools
      (Nova Micro)    (add_numbers)
```

**Infrastructure:** AWS CDK / CloudFormation

**Observability:** Amazon CloudWatch Logs

**Runtime identity:** Dedicated IAM execution role with a customer-managed permissions boundary

## Security

The project follows a least-privilege security approach.

### Developer Access

- AWS credentials are not stored in application source code.
- Developer access uses AWS IAM Identity Center with MFA and temporary SSO credentials.
- Local configuration and deployment state are excluded from Git.
- Read-only and administrative AWS CLI profiles are used for different tasks.

### Runtime Permissions

- The AgentCore Runtime uses a dedicated IAM execution role.
- A customer-managed IAM permissions boundary named `AWSStudyCoachRuntimeBoundary` has been created and applied to that role.
- The boundary limits the maximum permissions available to the Runtime execution role.
- The boundary policy was validated with AWS IAM Access Analyzer.
- A live cloud invocation was successfully tested after the boundary was applied.
- The test confirmed an `add_numbers` tool call with inputs `7` and `5`, producing the result `12`.

An IAM permissions boundary is not a permission grant by itself. Effective permissions depend on the role's other applicable IAM policies and controls.

### Deployment Permissions

- A separate IAM role, `StudyCoachCloudFormationExecutionRole`, has been created.
- Scoped initial permissions have been added and tested using IAM Policy Simulator.
- The role has **not** been assigned to the existing CloudFormation stack.
- The current CDK deployment path has not yet been migrated to this restricted role.
- The least-privilege CloudFormation execution policy remains under development and must not be treated as production-ready.

Security documentation and policy templates are maintained in the `security/` directory.

## Infrastructure and Deployment Status

The application is deployed to Amazon Bedrock AgentCore Runtime in AWS Region `eu-central-1`.

The CDK configuration includes the intended permissions boundary and project resource tags.

The permissions boundary has already been applied manually to the live execution role. A CloudFormation change set has been created to bring the deployed template into alignment with that boundary, but the change set has **not yet been executed**.

The current CDK diff also includes a CodeZip artifact change. To avoid an unrelated application update during the IAM security migration, a separate boundary-only CloudFormation template was prepared and validated.

**Do not execute an unrestricted `cdk deploy` until the CodeZip difference and deployment permissions have been reviewed.**

## Validation

The following checks have been completed:

- TypeScript CDK build
- CDK synthesis and diff inspection
- IAM permissions boundary policy validation
- IAM policy simulation for selected deployment actions
- CloudFormation template validation
- Successful direct AgentCore Runtime invocation after applying the boundary
- Successful `add_numbers(7, 5)` tool execution

These checks validate the current prototype and selected security scenarios. They do not replace automated regression testing or a complete security review.

## Known Issues and Future Work

- OpenTelemetry span export returned HTTP 400 during earlier testing. Agent invocation and tool execution succeeded; observability investigation remains open.
- Agent streaming output included internal `<thinking>` text. Response filtering should be reviewed before exposing the agent to end users.
- The CDK diff includes an unintended CodeZip artifact change.
- The CloudFormation execution role requires additional least-privilege design and rollback validation before it can be used for stack deployments.
- Automated tests and certification study tools are not yet implemented.

## Project Status

**Active development: cloud prototype deployed, security hardening in progress.**

Amazon Bedrock inference and Python tool execution have been verified successfully with the Runtime permissions boundary in place.

Next milestones include CloudFormation security alignment, least-privilege deployment, certification study tools, automated testing, and improved observability.

## Study Materials Search

The agent includes a Strands SDK tool named search_study_materials for keyword-based searches across curated AWS documentation for S3, IAM, and Lambda.

The search is case-insensitive and handles empty or unknown queries.

Seven unit tests passed locally using Python unittest.

Run tests: `.\app\agent\.venv\Scripts\python.exe -m unittest discover -s test -p test_*.py -v` 

Cloud integration testing for this new tool is pending.

### AWS S3 Lab Integration Validation


## AWS Certification Practice and Hands-on Labs

AWS Study Coach supports both certification practice questions and
hands-on AWS laboratory exercises with automated verification.

### Practice Questions

The agent provides AWS certification-style questions with multiple-choice
answers and explanations.

Available tools:

- `generate_practice_question`: Get a practice question by AWS topic.
- `check_practice_answer`: Check a selected answer and return an explanation.

Currently supported question topics:
- Amazon S3
- AWS IAM

Questions are currently curated and predefined. Dynamic question
generation is planned for a future iteration.

### Hands-on AWS Labs

The agent can assign practical AWS exercises and verify their completion
using real AWS API calls.

Available tools:

- `generate_lab_task`: Get instructions for an AWS lab.
- `verify_lab_task`: Verify lab resources using boto3.

#### Lab 001: Secure Amazon S3 Bucket

The student must:

1. Create an S3 bucket with the prefix `study-coach-lab-`.
2. Enable S3 Versioning.
3. Enable all four S3 Block Public Access settings.
4. Configure default SSE-S3 encryption (AES256).

The verifier checks the bucket configuration using read-only AWS API calls.

It also validates:
- Expected AWS account ownership
- AWS region (`eu-central-1`)
- API access errors separately from failed configuration checks

### Real AWS Integration Test

Successfully tested in AWS `eu-central-1`.

| Verification | Result |
|---|---|
| Bucket ownership | PASS |
| Region validation | PASS |
| S3 Versioning | PASS |
| Block Public Access | PASS |
| Default Encryption (AES256) | PASS |
| Lab score | **3/3** |

The Strands Agent successfully invoked `verify_lab_task` through
Amazon Bedrock Nova Micro and returned the verification results with
explanations.

### Running Unit Tests

From the repository root:

```powershell
& .\app\agent\.venv\Scripts\python.exe -m unittest discover -s test -p "test_*.py" -v
```

Latest local validation: **17 tests passed**.

### Security and Limitations

- AWS resources are created manually by the student.
- Lab verification uses read-only S3 API operations.
- The verifier requires `AWS_STUDY_ACCOUNT_ID`.
- Lab bucket names must start with `study-coach-lab-`.
- The current S3 lab is restricted to `eu-central-1`.
- Local end-to-end testing used an existing AWS SSO profile with Bedrock access.
- A dedicated least-privilege runtime role is still required before cloud deployment.
- The practice tools have not yet been deployed to AgentCore Runtime.

### Planned Improvements

- Additional questions for Lambda, EC2, VPC, and IAM.
- More hands-on labs with automated verification.
- Dedicated least-privilege permissions for the lab verifier.
- Student progress tracking and lab history.
- Integration with the deployed Amazon Bedrock AgentCore Runtime.
```
### AWS Lambda Lab Integration Validation

Successfully validated the Lambda configuration lab against a real AWS Lambda function in `eu-central-1`.

- Lambda runtime: Python 3.12
- Memory: 128 MB
- Timeout: 10 seconds
- Function state: Active
- Execution role: AWS account ownership verified
- Result: **5/5 checks passed**

The Strands Agent successfully invoked `verify_lambda_lab_task` using Amazon Bedrock Nova Micro and returned the verification results with explanations.

Lambda configuration verification uses read-only AWS API calls. The production AgentCore deployment is pending.

## AWS Certification Question Bank and Hands-on Labs

AWS Study Coach combines certification preparation with practical AWS exercises and automated resource verification.

### Certification Question Bank

- 50 curated multiple-choice questions.
- Supported topics: Amazon S3, IAM, Lambda, EC2, and VPC.
- 10 questions per topic.
- Difficulty filtering and randomized question selection.
- Answer validation with explanations.
- Questions stored in `app/agent/data/questions.json`.

### Hands-on AWS Labs

| Lab | Verification | Real AWS Test |
|---|---|---|
| S3 Secure Bucket | Versioning, Block Public Access, encryption | 3/3 PASS |
| Lambda Configuration | Runtime, memory, timeout, state, execution role | 5/5 PASS |
| IAM Least Privilege | Trust policy, inline policy, attached policies, allowed action and resource scope | 5/5 PASS |

Verification is implemented with `boto3` using read-only AWS API operations.

### End-to-End Integration

All three labs were successfully verified through Strands Agent using Amazon Bedrock Nova Micro.

The agent invoked the appropriate verification tools and explained the results.

### Testing

- 39 unit tests passed.
- S3, Lambda, and IAM labs validated against real AWS resources.
- AWS region: `eu-central-1`.

### Security and Limitations

- Lab resources are created manually by the student.
- Verification tools do not create, modify, or delete AWS resources.
- Local integration tests used AWS IAM Identity Center credentials.
- IAM Lab checks a prescribed policy configuration, not every possible effective IAM permission.
- A dedicated least-privilege role is required for production AgentCore deployment.
- These new features are not yet deployed to AgentCore Runtime.

### Future Improvements

- Exam mode with scoring across multiple questions.
- Student progress tracking.
- Additional EC2 and VPC hands-on labs.
- Least-privilege AgentCore deployment.