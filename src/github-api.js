const API_BASE_URL = 'https://api.github.com';
const API_VERSION = '2022-11-28';
const MAX_PAGE_SIZE = 30;
const MAX_TEXT_LENGTH = 12_000;

export function validateRepository(owner, repo) {
  const validOwner = /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/;
  const validRepo = /^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$/;
  if (typeof owner !== 'string' || !validOwner.test(owner) || owner.length > 39) {
    throw new TypeError('Invalid GitHub owner.');
  }
  if (typeof repo !== 'string' || !validRepo.test(repo) || repo.length > 100) {
    throw new TypeError('Invalid GitHub repository name.');
  }
  return { owner, repo };
}

export function clampPageSize(value = 10) {
  if (!Number.isInteger(value) || value < 1) {
    throw new TypeError('per_page must be a positive integer.');
  }
  return Math.min(value, MAX_PAGE_SIZE);
}

export function safeRepositoryPath(owner, repo, suffix = '') {
  const identity = validateRepository(owner, repo);
  if (typeof suffix !== 'string' || !/^[A-Za-z0-9/_-]*(?:\?[A-Za-z0-9_=&%-]*)?$/.test(suffix)) {
    throw new TypeError('Invalid GitHub API path suffix.');
  }
  const prefix = `/repos/${encodeURIComponent(identity.owner)}/${encodeURIComponent(identity.repo)}`;
  const normalizedSuffix = suffix ? `/${suffix.replace(/^\/+/, '')}` : '';
  const url = new URL(`${prefix}${normalizedSuffix}`, API_BASE_URL);
  if (url.origin !== API_BASE_URL) throw new TypeError('GitHub API host is fixed.');
  return url;
}

export async function githubGet(url, token, fetchImpl = fetch) {
  if (!token || typeof token !== 'string' || token.trim().length < 10) {
    throw new Error('GITHUB_TOKEN is required. Configure a fine-grained read-only token.');
  }
  const parsed = new URL(url);
  if (parsed.origin !== API_BASE_URL || !parsed.pathname.startsWith('/repos/')) {
    throw new TypeError('Only GitHub repository GET endpoints are permitted.');
  }

  const response = await fetchImpl(parsed, {
    method: 'GET',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': API_VERSION,
      'User-Agent': 'CLT-GitHub-MCP/0.1.0'
    },
    signal: AbortSignal.timeout(15_000)
  });

  if (!response.ok) {
    const detail = response.status === 403
      ? 'GitHub denied the request or the API rate limit was reached.'
      : response.status === 404
        ? 'Repository or resource not found, or token lacks access.'
        : `GitHub API request failed (${response.status}).`;
    throw new Error(detail);
  }
  return response.json();
}

export function normalizeIssue(issue) {
  return {
    number: issue.number,
    title: issue.title,
    state: issue.state,
    url: issue.html_url,
    created_at: issue.created_at,
    updated_at: issue.updated_at,
    labels: (issue.labels ?? []).map(label => typeof label === 'string' ? label : label.name),
    assignees: (issue.assignees ?? []).map(user => user.login),
    body: String(issue.body ?? '').slice(0, MAX_TEXT_LENGTH)
  };
}

export function normalizePullRequest(pr) {
  return {
    number: pr.number,
    title: pr.title,
    state: pr.state,
    draft: Boolean(pr.draft),
    url: pr.html_url,
    head: pr.head?.ref,
    base: pr.base?.ref,
    created_at: pr.created_at,
    updated_at: pr.updated_at
  };
}

export function normalizeWorkflowRun(run) {
  return {
    id: run.id,
    name: run.name,
    workflow: run.path,
    status: run.status,
    conclusion: run.conclusion,
    event: run.event,
    branch: run.head_branch,
    commit: run.head_sha,
    url: run.html_url,
    created_at: run.created_at,
    updated_at: run.updated_at
  };
}

export { MAX_PAGE_SIZE };
