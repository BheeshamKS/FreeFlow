---
name: finalize
description: Complete project finalization with quality gates and git workflow automation.
---

# Finalize

## Usage
```
/finalize [commit-message] [--skip-docs] [--skip-lint] [--skip-types] [--skip-build] [--dry-run] [--no-push]
```

## Workflow Pipeline
1. Update documentation (.md files) with latest changes
2. Detect Next.js version from package.json
3. **If Next.js < 16**: Run `bun lint` for code quality validation
4. Run `bun type` for TypeScript type checking
5. Run `bun build` for compilation verification
6. Generate structured commit message if not provided
7. Git add, commit, and push if all gates pass

> **Note**: Next.js 16+ removed `next lint`. The command auto-detects the version and skips linting for Next.js 16+.

## Auto-Persona Activation
- **DevOps**: Infrastructure and deployment automation
- **QA**: Quality assurance and testing validation
- **Scribe**: Professional commit message generation

## MCP Integration
- **Sequential**: Workflow coordination and systematic validation
- **Context7**: Best practices and commit message patterns

## Arguments
- `[commit-message]` - Custom commit message (optional)
- `--skip-docs` - Skip documentation updates
- `--skip-lint` - Skip linting validation (only applies to Next.js < 16)
- `--skip-types` - Skip TypeScript type checking
- `--skip-build` - Skip build verification
- `--dry-run` - Show what would be done without executing
- `--no-push` - Commit locally but don't push to remote

## Examples
```bash
# Full workflow with custom message
/finalize "feat: add user authentication system"

# Skip some steps
/finalize --skip-docs --skip-build

# Dry run to see what would happen
/finalize --dry-run

# Commit locally only
/finalize "fix: resolve login bug" --no-push
```
