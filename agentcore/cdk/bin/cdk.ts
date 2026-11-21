#!/usr/bin/env node
import { App } from 'aws-cdk-lib';
import { AgentCoreProjectSpecSchema, readAgentCoreProject, resolveTargetStacks, transformAgentCoreJson } from '@aws/agentcore-cdk';
import { AgentCoreStack } from '../lib/cdk-stack';
import { resolve } from 'node:path';
import { withRuntimeSource } from '../lib/runtime-source';
import { execFileSync } from 'node:child_process';
import { applyLockedDependencies } from '../lib/locked-dependencies';

try {
  // The AgentCore CLI runs this app from agentcore/cdk/; readAgentCoreProject walks up to agentcore/.
  const project = readAgentCoreProject();
  const spec = AgentCoreProjectSpecSchema.parse(project.agentCoreJson);
  withRuntimeSource(resolve(project.projectRoot, 'app/agent'), (codeLocation) => {
    const requirements = execFileSync('uv', [
      'export', '--locked', '--no-dev', '--no-emit-project', '--no-hashes',
      '--no-header', '--format', 'requirements-txt', '--project',
      resolve(project.projectRoot, 'app/agent'),
    ], { encoding: 'utf8' });
    applyLockedDependencies(codeLocation, requirements);
    const agentCoreJson = {
      ...spec,
      runtimes: spec.runtimes.map((runtime) =>
        runtime.name === 'agent' && runtime.build === 'CodeZip'
          ? { ...runtime, codeLocation }
          : runtime
      ),
    };
    const app = new App();
    for (const stack of resolveTargetStacks({
      projectName: project.projectName,
      targets: project.targets,
      deployedState: project.deployedState,
    })) {
      new AgentCoreStack(app, stack.stackName, {
        env: stack.env,
        tags: stack.tags,
        description: stack.description,
        application: transformAgentCoreJson(agentCoreJson, {
          projectRoot: project.projectRoot,
          credentials: stack.credentials,
          target: stack.target,
        }),
      });
    }
    app.synth();
  });
} catch (error) {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exit(1);
}
