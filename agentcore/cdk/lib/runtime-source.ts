import { copyFileSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

// The CodeZip packager in agentcore-cdk 1.0.2 does not honor .gitignore.
// Only these reviewed application files may enter the runtime bundle.
export const RUNTIME_SOURCE_FILES = [
  'README.md',
  'pyproject.toml',
  'uv.lock',
  'main.py',
  'parse.py',
  'practice.py',
  'question_bank.py',
  'study_materials.py',
  'exam_mode.py',
  'progress.py',
  'lambda_lab.py',
  'iam_lab.py',
  'model/__init__.py',
  'model/load.py',
  'memory/__init__.py',
  'memory/session.py',
  'data/questions.json',
] as const;

export function withRuntimeSource<T>(source: string, build: (directory: string) => T): T {
  const temporaryRoot = resolve(tmpdir());
  const staging = mkdtempSync(join(temporaryRoot, 'study-coach-source-'));
  try {
    for (const relative of RUNTIME_SOURCE_FILES) {
      const destination = join(staging, relative);
      mkdirSync(dirname(destination), { recursive: true });
      copyFileSync(join(source, relative), destination);
    }
    return build(staging);
  } finally {
    // Remove only the exact temporary directory created by this invocation.
    if (dirname(resolve(staging)) !== temporaryRoot) {
      throw new Error('Runtime source staging escaped its temporary directory');
    }
    rmSync(staging, { recursive: true, force: true });
  }
}
