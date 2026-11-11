import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clampPageSize,
  githubGet,
  normalizeIssue,
  normalizePullRequest,
  normalizeWorkflowRun,
  safeRepositoryPath,
  validateRepository
} from '../src/github-api.js';

test('validates repository identity and rejects path injection', () => {
  assert.deepEqual(validateRepository('octo-org', 'project_1.v2'), { owner: 'octo-org', repo: 'project_1.v2' });
  assert.throws(() => validateRepository('../evil', 'repo'), /owner/);
  assert.throws(() => validateRepository('owner', 'repo/../../secrets'), /repository/);
});

test('builds repository API URLs on the fixed GitHub host', () => {
  assert.equal(safeRepositoryPath('octo', 'repo', 'issues').href, 'https://api.github.com/repos/octo/repo/issues');
  assert.throws(() => safeRepositoryPath('octo', 'repo', '../users'), /path suffix/);
  assert.throws(() => safeRepositoryPath('octo', 'repo', 'https://evil.example'), /path suffix/);
});

test('clamps result sizes and rejects invalid page sizes', () => {
  assert.equal(clampPageSize(100), 30);
  assert.equal(clampPageSize(5), 5);
  assert.throws(() => clampPageSize(0), /positive integer/);
  assert.throws(() => clampPageSize(1.5), /positive integer/);
});

test('requires a token and sends only GET requests to GitHub repository endpoints', async () => {
  await assert.rejects(() => githubGet('https://api.github.com/repos/o/r', ''), /GITHUB_TOKEN/);
  await assert.rejects(() => githubGet('https://example.com/repos/o/r', '1234567890'), /Only GitHub/);
  let observed;
  const result = await githubGet('https://api.github.com/repos/o/r', '1234567890', async (url, options) => {
    observed = { url: url.href, method: options.method, auth: options.headers.Authorization };
    return { ok: true, json: async () => ({ full_name: 'o/r' }) };
  });
  assert.deepEqual(result, { full_name: 'o/r' });
  assert.deepEqual(observed, {
    url: 'https://api.github.com/repos/o/r',
    method: 'GET',
    auth: 'Bearer 1234567890'
  });
});

test('normalizes issue, pull request, and workflow run payloads', () => {
  assert.deepEqual(normalizeIssue({ number: 2, title: 'Bug', state: 'open', labels: [{ name: 'bug' }], assignees: [{ login: 'dev' }] }), {
    number: 2, title: 'Bug', state: 'open', url: undefined, created_at: undefined, updated_at: undefined,
    labels: ['bug'], assignees: ['dev'], body: ''
  });
  assert.equal(normalizePullRequest({ number: 3, title: 'Feature', state: 'open', draft: true, head: { ref: 'feat' }, base: { ref: 'main' } }).draft, true);
  assert.equal(normalizeWorkflowRun({ id: 9, conclusion: 'success', head_branch: 'main' }).conclusion, 'success');
});
