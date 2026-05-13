# Codex Installation

OpenAI Codex discovers repository skills from `.agents/skills` under the working tree, and user skills from `$HOME/.agents/skills`.

This package intentionally lives under `packages/esdata-chatgpt-skills` so it can be versioned and zipped. To make the skills active in Codex, install them into one of the discovery locations.

## Repository Install

From the repository root:

```powershell
New-Item -ItemType Directory -Force .agents\skills | Out-Null
Copy-Item packages\esdata-chatgpt-skills\skills\* .agents\skills\ -Recurse -Force
```

Restart Codex if the new skills do not appear.

## User Install

```powershell
New-Item -ItemType Directory -Force $HOME\.agents\skills | Out-Null
Copy-Item G:\_Proyectos\esdata\packages\esdata-chatgpt-skills\skills\* $HOME\.agents\skills\ -Recurse -Force
```

## Disable A Skill

Add a per-skill override to `~/.codex/config.toml`:

```toml
[[skills.config]]
path = "G:/_Proyectos/esdata/packages/esdata-chatgpt-skills/skills/esdata-fatca-crs-review/SKILL.md"
enabled = false
```

## Recommended Active Set

Enable all six skills for ESData workflows. Use `esdata-mcp-truth-contract` as the baseline skill whenever a prompt asks the model to rely on ESData MCP.
