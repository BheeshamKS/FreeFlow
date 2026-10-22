# FreeFlow Project Agent Instructions

This repository is governed by the primary orchestrator skill defined at [`.agents/skills/freeflow-lead/SKILL.md`](file:///.agents/skills/freeflow-lead/SKILL.md).

## Mandatory Execution Protocols

1. **Every Prompt Skill Suite Activation:**
   On every user request, you must systematically orchestrate and apply the relevant skills from this suite:
   - `/implement` — Clean code implementation and architecture
   - `/diagnosing-bugs` — Root-cause debugging loops with minimal failing tests
   - `/troubleshoot` — Systematic triage and error recovery
   - `/security-and-hardening` — Redacting `gsk_...` keys, sanitizing logs, and safe execution
   - `/design-taste-frontend` — Dark frosted obsidian glass aesthetic, clean typography, anti-slop UI
   - `/generative_ui` — Interactive UI widgets and harmonic visualizations
   - `/frontend-visual-qa` — Visual inspection of HUD capsule, dialogs, and scaling
   - `/ui-test` — Headless Qt (`offscreen`) testing and event validation
   - `/code-documenter` & `/document` & `/documenter` — Comprehensive technical and user documentation
   - `/banana` — Design systems, badges, and visual assets
   - `/git-workflow-manager` — Clean atomic commits, git hygiene, and release tags
   - `/finalize` — Verification quality gates before cutting releases
   - `/find-skills` — Specialized skill discovery
   - `/multi-agent-coordinator` — Multi-agent task coordination

2. **Release History Protocol:**
   In **every release**, you MUST update the cumulative release log in [`.agents/skills/freeflow-lead/SKILL.md`](file:///.agents/skills/freeflow-lead/SKILL.md) and [`CHANGELOG.md`](file:///CHANGELOG.md) with a summary of newly added features, resolved bugs, and verification results.

3. **Author & Commit Identity:**
   Always author Git commits with:
   `BheeshamKS <bheehamkumarsajnani3@gmail.com>`
   using `--author="BheeshamKS <bheehamkumarsajnani3@gmail.com>"`.
