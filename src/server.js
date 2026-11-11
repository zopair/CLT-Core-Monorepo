#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import {
  clampPageSize,
  githubGet,
  normalizeIssue,
  normalizePullRequest,
  normalizeWorkflowRun,
  safeRepositoryPath
} from './github-api.js';

const token = process.env.GITHUB_TOKEN;
const server = new McpServer({
  name: 'clt-github-readonly',
  version: '0.1.0'
});

function textResult(value) {
  return { content: [{ type: 'text', text: JSON.stringify(value, null, 2) }] };
}

function registerReadTool(name, description, schema, handler) {
  server.registerTool(name, {
    description,
    inputSchema: schema,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true }
  }, async (args) => {
    try {
      return textResult(await handler(args));
    } catch (error) {
      return { isError: true, content: [{ type: 'text', text: error.message }] };
    }
  });
}

const repoFields = {
  owner: z.string().min(1).max(39).describe('GitHub owner or organization'),
  repo: z.string().min(1).max(100).describe('Repository name')
};
const pageField = z.number().int().min(1).max(30).optional().describe('Maximum records to return (1-30)');

registerReadTool(
  'github_repository_overview',
  'Read repository metadata, default branch, visibility, language, and repository URLs. Read-only.',
  repoFields,
  async ({ owner, repo }) => {
    const url = safeRepositoryPath(owner, repo);
    const data = await githubGet(url, token);
    return {
      full_name: data.full_name,
      description: data.description,
      private: data.private,
      archived: data.archived,
      default_branch: data.default_branch,
      language: data.language,
      topics: data.topics ?? [],
      open_issues_count: data.open_issues_count,
      pushed_at: data.pushed_at,
      html_url: data.html_url
    };
  }
);

registerReadTool(
  'github_list_issues',
  'List repository issues (pull requests are excluded by GitHub). Read-only.',
  { ...repoFields, state: z.enum(['open', 'closed', 'all']).default('open'), per_page: pageField },
  async ({ owner, repo, state, per_page }) => {
    const size = clampPageSize(per_page ?? 10);
    const url = safeRepositoryPath(owner, repo, `issues?state=${state}&per_page=${size}&sort=updated&direction=desc`);
    const data = await githubGet(url, token);
    return data.filter(item => !item.pull_request).map(normalizeIssue);
  }
);

registerReadTool(
  'github_list_pull_requests',
  'List repository pull requests with branch and draft metadata. Read-only.',
  { ...repoFields, state: z.enum(['open', 'closed', 'all']).default('open'), per_page: pageField },
  async ({ owner, repo, state, per_page }) => {
    const size = clampPageSize(per_page ?? 10);
    const url = safeRepositoryPath(owner, repo, `pulls?state=${state}&per_page=${size}&sort=updated&direction=desc`);
    return (await githubGet(url, token)).map(normalizePullRequest);
  }
);

registerReadTool(
  'github_list_workflow_runs',
  'List recent GitHub Actions workflow runs and their conclusions. Read-only.',
  { ...repoFields, per_page: pageField },
  async ({ owner, repo, per_page }) => {
    const size = clampPageSize(per_page ?? 10);
    const url = safeRepositoryPath(owner, repo, `actions/runs?per_page=${size}`);
    const data = await githubGet(url, token);
    return (data.workflow_runs ?? []).map(normalizeWorkflowRun);
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
