# Configure the CLT GitHub MCP server in GitHub Copilot

This project prepares a read-only MCP server. GitHub does **not** load repository-level Copilot MCP settings from a committed JSON file: an administrator must paste the configuration into the repository's Copilot MCP settings page and save it.

## 1. Add the Agent secret

In the repository where Copilot Cloud Agent / Code Review should use the server:

1. Open **Settings → Secrets and variables → Copilot** (the exact navigation label can vary by GitHub UI rollout).
2. Add an **Agent secret** named `COPILOT_MCP_GITHUB_TOKEN`.
3. Use a fine-grained personal access token restricted to only the required repositories, with read-only permissions:
   - Metadata: read-only
   - Contents: read-only
   - Issues: read-only
   - Pull requests: read-only
   - Actions: read-only (only if workflow runs are required)
4. Do not paste the token into the MCP JSON or commit it to the repository.

## 2. Add the repository MCP configuration

Open **Settings → Code, planning, and automation → Copilot → MCP servers** and paste this JSON after the package is merged into the default branch:

```json
{
  "mcpServers": {
    "clt-github-readonly": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "github:zopair/CLT-Core-Monorepo#main"],
      "env": {
        "GITHUB_TOKEN": "$COPILOT_MCP_GITHUB_TOKEN"
      },
      "tools": [
        "github_repository_overview",
        "github_list_issues",
        "github_list_pull_requests",
        "github_list_workflow_runs"
      ]
    }
  }
}
```

Save the MCP configuration. GitHub validates its JSON syntax. The GitHub-provided MCP server and Playwright MCP server can remain enabled separately.

## 3. Verify in Copilot Cloud Agent

1. Create a low-risk test issue in this repository and assign it to Copilot.
2. Open the resulting Copilot session and its logs.
3. Expand **Start MCP Servers** and verify that `clt-github-readonly` starts and lists the four allowlisted tools.
4. Ask Copilot to inspect repository metadata and list recent Actions runs. Confirm that the session logs show the expected tool calls.
5. Do not grant write tools to this server as part of the initial rollout.

Copilot Code Review can also use the repository MCP configuration, but its tool compatibility requires read-only annotations. The current rollout should first be verified with Cloud Agent; do not assume that a successful server startup proves every Copilot surface is connected.

## Scope and limitations

- This configuration is for repository-level Copilot Cloud Agent, Automations, and Code Review—not a global connector installation for every Copilot Chat surface.
- Repository MCP configuration is saved in GitHub Settings, not in Git history. An administrator must perform steps 1–2.
- Copilot MCP tools may be invoked autonomously. Keep the token read-only and tool allowlist narrow.
- This project does not read, export, or reuse the GitHub App credentials used by ChatGPT's GitHub connector.
