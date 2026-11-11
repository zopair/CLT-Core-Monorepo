import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const serverPath = fileURLToPath(new URL('../src/server.js', import.meta.url));

test('starts over stdio and advertises only the four read-only GitHub tools', async () => {
  const client = new Client({ name: 'clt-github-mcp-smoke-test', version: '1.0.0' });
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [serverPath],
    env: { ...process.env, GITHUB_TOKEN: 'smoke-test-token-not-used-for-network' }
  });

  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    const names = tools.map(tool => tool.name).sort();
    assert.deepEqual(names, [
      'github_list_issues',
      'github_list_pull_requests',
      'github_list_workflow_runs',
      'github_repository_overview'
    ]);
    for (const tool of tools) {
      assert.equal(tool.annotations?.readOnlyHint, true, `${tool.name} must be marked read-only`);
      assert.equal(tool.annotations?.destructiveHint, false, `${tool.name} must not be destructive`);
    }
  } finally {
    await client.close();
  }
});
