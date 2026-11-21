import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export function applyLockedDependencies(directory: string, requirements: string): void {
  const entries = requirements.split(/\r?\n/).map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));
  if (!entries.length || entries.some((line) => !/^[A-Za-z0-9_.-]+==[^\s;]+(?:\s*;.*)?$/.test(line))) {
    throw new Error('Expected pinned requirements from uv export; refusing an unlocked build');
  }
  const path = join(directory, 'pyproject.toml');
  const source = readFileSync(path, 'utf8');
  const block = /^dependencies\s*=\s*\[[\s\S]*?^\]/m;
  if (!block.test(source)) {
    throw new Error('Cannot find the staged project dependency block');
  }
  writeFileSync(path, source.replace(block,
    `dependencies = [\n${entries.map((entry) => `    ${JSON.stringify(entry)},`).join('\n')}\n]`));
}
