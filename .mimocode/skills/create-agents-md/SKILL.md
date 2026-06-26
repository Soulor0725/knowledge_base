---
name: create-agents-md
description: Create or update AGENTS.md for a project — compact instruction file for future AI sessions
---

# Create or Update AGENTS.md

Generate a concise `AGENTS.md` at the project root that helps future coding sessions avoid mistakes and ramp up quickly.

## When to use

- First time setting up a new project
- After major architecture changes
- When onboarding an existing project with no AGENTS.md

## Procedure

### 1. Discover project structure

```
- Read root directory listing
- Read key config files: package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, etc.
- Check for CI/CD: .github/workflows/, .gitlab-ci.yml, Jenkinsfile
- Check for Docker: Dockerfile, docker-compose.yml
- Check for test directories and frameworks
- Read README.md if present
- Read existing .env.example or config files
```

### 2. Analyze conventions

Identify from code:
- Language and framework
- Project type (library, CLI, web app, API, monorepo)
- Directory structure convention
- Test framework and test directory layout
- Build/run commands
- Key architectural patterns (dependency injection, plugin system, etc.)
- Linting/formatting tools
- Database and ORM if any
- Environment variable requirements

### 3. Write AGENTS.md

Structure (keep it compact — every line should answer "Would an AI agent need this?"):

```markdown
# AGENTS.md

## What this is
<1-2 sentences: language, framework, purpose>

## Key commands
<run, test, build, lint — exact commands>

## Architecture notes
<directory layout, key patterns, gotchas>

## Gotchas
<things that trip up AI agents: hidden configs, non-obvious conventions, common mistakes>
```

### 4. Validate

- Verify all referenced file paths exist (Glob)
- Verify all referenced commands are runnable (Bash dry-run if safe)
- Ensure no secrets or credentials are included
- Keep under 150 lines — brevity is the point

## Output

A single `AGENTS.md` file at the project root.

## Examples from this workspace

Two prior uses:
- `E:\trae_projects\AGENTS.md` — multi-project workspace overview
- `E:\trae_projects\student_management\AGENTS.md` — Flask app with test suite

Both followed the same structure: What this is → Key commands → Architecture notes → Gotchas.
