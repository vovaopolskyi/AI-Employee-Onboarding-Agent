import { AgentCoreApplication, type AgentCoreApplicationProps } from '@aws/agentcore-cdk';
import { ArnFormat, Stack, Tags, type StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
export interface AgentCoreStackProps extends StackProps {
  /** Props for the AgentCore application, produced by transformAgentCoreJson from agentcore/agentcore.json. */
  application: AgentCoreApplicationProps;
}

/**
 * The stack the AgentCore CLI deploys. Everything declared in agentcore/agentcore.json is
 * created by the AgentCoreApplication construct. Add your own resources below it and wire
 * them to your runtimes and harnesses through the application's accessors.
 */
export class AgentCoreStack extends Stack {
  public readonly application: AgentCoreApplication;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);
    this.application = new AgentCoreApplication(this, 'Application', props.application);
    const runtimeBoundary = iam.ManagedPolicy.fromManagedPolicyName(
      this,
      'RuntimePermissionsBoundary',
      'AWSStudyCoachRuntimeBoundary'
    );

    iam.PermissionsBoundary.of(this.application).apply(runtimeBoundary);
        // Restrict the generated Runtime identity policy to Claude Haiku 4.5.
    const runtimePolicies = this.node.findAll().filter(
      (resource): resource is iam.CfnPolicy =>
        resource instanceof iam.CfnPolicy &&
        this.getLogicalId(resource) ===
          'ApplicationRuntimeAgentRuntimeExecutionRoleDefaultPolicy3DC31095'
    );

    if (runtimePolicies.length !== 1) {
      throw new Error(
        `Expected one Runtime IAM policy, found ${runtimePolicies.length}`
      );
    }

    const runtimePolicy = runtimePolicies[0];
    const document = this.resolve(runtimePolicy.policyDocument) as {
      Version?: string;
      Statement?: Array<{
        Action?: string | string[];
        Resource?: string | string[];
        [key: string]: unknown;
      }>;
    };

    if (!Array.isArray(document.Statement)) {
      throw new Error('Runtime IAM Policy has no Statement array');
    }

    const bedrockStatements = document.Statement.filter((statement) =>
      [statement.Action].flat().some(
        (action) => typeof action === 'string' && action.startsWith('bedrock:')
      )
    );

    if (
      bedrockStatements.length !== 1 ||
      ![bedrockStatements[0].Action].flat().includes('bedrock:InvokeModel')
    ) {
      throw new Error('Unexpected Bedrock policy structure; refusing to modify it');
    }

    const profileArn = Stack.of(this).formatArn({
      service: 'bedrock',
      region: 'eu-central-1',
      resource: 'inference-profile',
      resourceName: 'eu.anthropic.claude-haiku-4-5-20251001-v1:0',
      arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
    });

    const modelArn = (region: string) =>
      `arn:aws:bedrock:${region}::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0`;

    const claudeStatements = [
      {
        Sid: 'InvokeClaudeInferenceProfile',
        Effect: 'Allow',
        Action: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        Resource: profileArn,
      },
      {
        Sid: 'InvokeClaudeModelsViaProfile',
        Effect: 'Allow',
        Action: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        Resource: [
          'eu-central-1',
          'eu-north-1',
          'eu-west-1',
          'eu-west-3',
          'eu-south-1',
          'eu-south-2',
        ].map(modelArn),
        Condition: {
          StringEquals: {
            'bedrock:InferenceProfileArn': profileArn,
          },
        },
      },
    ];

    const otherStatements = document.Statement.filter(
      (statement) => !bedrockStatements.includes(statement)
    );

        // Preserve the existing CloudFormation-managed CDK assets access.
    // Review and narrow these permissions separately after deployment.
    const assetsBucketArn =
      `arn:${Stack.of(this).partition}:s3:::cdk-hnb659fds-assets-` +
      `${Stack.of(this).account}-${Stack.of(this).region}`;

    runtimePolicy.addPropertyOverride('PolicyDocument.Statement', [
      ...otherStatements,
      {
        Effect: 'Allow',
        Action: ['s3:GetBucket*', 's3:GetObject*', 's3:List*'],
        Resource: [
          assetsBucketArn,
          `${assetsBucketArn}/*`,
        ],
      },
      ...claudeStatements,
    ]);

    // Example: give a runtime a DynamoDB table.
    //
    // import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
    // const orders = new dynamodb.Table(this, 'Orders', {
    //   partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
    // });
    // const checkout = this.application.runtime('checkout'); // or .harness('support')
    // checkout.grantReadWrite(orders);
    // checkout.addEnvironmentVariable('ORDERS_TABLE', orders.tableName);
    Tags.of(this).add('Project', 'AWSStudyCoach');
    Tags.of(this).add('Environment', 'dev');
    Tags.of(this).add('ManagedBy', 'CDK');
  }
}
