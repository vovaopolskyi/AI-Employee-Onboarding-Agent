import { strict as assert } from 'node:assert';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { test } from 'node:test';
import { RUNTIME_SOURCE_FILES, withRuntimeSource } from '../lib/runtime-source';

test('bundle source includes the question bank but excludes local data and secrets', () => {
  const temporaryRoot = resolve(tmpdir());
  const source = mkdtempSync(join(temporaryRoot, 'study-coach-fixture-'));
  let staged = '';
  try {
    for (const relative of RUNTIME_SOURCE_FILES) {
      const path = join(source, relative);
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, `fixture:${relative}`);
    }
    for (const relative of ['data/student_progress.json', '.env', '.env.local', 'data/private.json']) {
      writeFileSync(join(source, relative), 'must never enter the bundle');
    }
    withRuntimeSource(source, (directory) => {
      staged = directory;
      assert.equal(readFileSync(join(directory, 'data/questions.json'), 'utf8'),
        'fixture:data/questions.json');
      for (const relative of ['data/student_progress.json', '.env', '.env.local', 'data/private.json']) {
        assert.equal(existsSync(join(directory, relative)), false, relative);
      }
    });
    assert.equal(existsSync(staged), false, 'staging must be cleaned after a successful build');
    assert.equal(existsSync(join(source, 'data/student_progress.json')), true,
      'the original student history must stay untouched');
    assert.throws(() => withRuntimeSource(source, (directory) => {
      staged = directory;
      throw new Error('build failed');
    }), /build failed/);
    assert.equal(existsSync(staged), false, 'staging must be cleaned after a failed build');
  } finally {
    assert.equal(dirname(resolve(source)), temporaryRoot);
    rmSync(source, { recursive: true, force: true });
  }
});
