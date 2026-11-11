# CLT GitHub MCP — read-only integration

A small, zero-hosting-cost Model Context Protocol server that exposes a deliberately limited set of GitHub repository tools to GitHub Copilot Cloud Agent, Copilot Automations, and Copilot Code Review.

## Design

- **Transport:** MCP over stdio; the Copilot runtime launches the process.
- **Runtime:** Node.js 20+.
- **Authentication:** a fine-grained GitHub token injected at runtime through `GITHUB_TOKEN`.
- **Permissions:** read-only API calls only. No write, merge, release, secret, or workflow-dispatch tools are registered.
- **Safety:** fixed `api.github.com` origin, repository identity validation, bounded result sizes, request timeout, concise normalized output.
- **Cost:** no hosted service or paid API is required. GitHub API rate limits still apply.

## Tools

| Tool | Purpose |
|---|---|
| `github_repository_overview` | Repository metadata and default branch |
| `github_list_issues` | Issues only; pull requests excluded |
| `github_list_pull_requests` | Pull request list and branch metadata |
| `github_list_workflow_runs` | Recent Actions runs and conclusions |

## Local development

```bash
npm install
npm test
npm start
```

The server communicates over stdin/stdout. Diagnostics must go to stderr; do not add console output to stdout.

## Security boundary

Create a fine-grained token scoped only to repositories Copilot needs. Grant **Metadata: read-only**, **Contents: read-only**, **Issues: read-only**, **Pull requests: read-only**, and **Actions: read-only** only if workflow visibility is needed. Store it as a Copilot Agent secret named `COPILOT_MCP_GITHUB_TOKEN`. Never commit the token or place it in a variable, config literal, issue, or prompt.

The server has no arbitrary URL tool and cannot mutate GitHub state. The GitHub MCP server already provided by GitHub may remain enabled independently.

## GitHub Copilot repository setup

Follow [`docs/GITHUB_COPILOT_SETUP.md`](docs/GITHUB_COPILOT_SETUP.md). Repository MCP configuration is entered in GitHub Settings; it is not activated merely by committing a config file.
