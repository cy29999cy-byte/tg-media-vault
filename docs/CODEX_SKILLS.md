# Codex Skill Pack for TG Media Vault

This project uses a small, explicit set of Agent Skills. The goal is not to install every trending skill; it is to make the project workflow reproducible and auditable.

## Principles

- Project-scoped installs only: keep skills with this repository rather than installing them globally.
- Pin the source repository by owner/name; do not install by ambiguous skill name alone.
- Review the source and license before adding or updating a skill.
- Skills guide the agent; they do not replace repository tests or CI.
- Never let a skill bypass Telegram access controls, credential hygiene, or the project guardrails in `CONTEXT.md` and `AGENTS.md`.

## Selected skills

| Skill | Source | Purpose |
| --- | --- | --- |
| `find-skills` | `vercel-labs/skills` | Search for existing Agent Skills before building new agent workflow logic. |
| `grill-with-docs` | `mattpocock/skills` | Stress-test a design and write durable context/ADR documentation. |
| `grilling` | `mattpocock/skills` | Systematic design-question tree used by `grill-with-docs`. |
| `domain-modeling` | `mattpocock/skills` | Maintain domain vocabulary, context, and architectural decisions. |
| `improve-codebase-architecture` | `mattpocock/skills` | Review coupling and architecture after features work. |
| `systematic-debugging` | `obra/superpowers` | Root-cause-first debugging instead of speculative patching. |
| `verification-before-completion` | `obra/superpowers` | Require fresh evidence before claiming a fix or task is complete. |
| `writing-plans` | `obra/superpowers` | Turn an agreed design into a concrete implementation sequence. |

The three source repositories are MIT-licensed at the time this document was created. Re-check upstream before future updates.

## Install in Codex

Run these commands from the repository root. They are intentionally project-scoped (no `-g`).

```bash
npx skills add vercel-labs/skills --skill find-skills -a codex -y

npx skills add mattpocock/skills --skill grill-with-docs -a codex -y
npx skills add mattpocock/skills --skill grilling -a codex -y
npx skills add mattpocock/skills --skill domain-modeling -a codex -y
npx skills add mattpocock/skills --skill improve-codebase-architecture -a codex -y

npx skills add obra/superpowers --skill systematic-debugging -a codex -y
npx skills add obra/superpowers --skill verification-before-completion -a codex -y
npx skills add obra/superpowers --skill writing-plans -a codex -y
```

After installation, verify that the project skills are present and inspect the generated lock/provenance data before committing it:

```bash
npx skills list
```

Codex project skills should be installed under `.agents/skills/`; the Skills CLI may also create `skills-lock.json` to record project-scoped provenance and content hashes. Review both before committing.

## Default project workflow

For a non-trivial feature, use this order:

1. Read `CONTEXT.md`, `AGENTS.md`, current ADRs, relevant code, and tests.
2. Use `find-skills` and GitHub search before proposing a greenfield implementation.
3. Use `grill-with-docs` / `domain-modeling` when decisions are not yet settled.
4. Use `writing-plans` to produce a small, testable implementation sequence.
5. Implement the smallest coherent slice.
6. Use `systematic-debugging` on failures; investigate root cause before changing code.
7. Run repository tests and checks.
8. Use `verification-before-completion` before saying the work is fixed or done.
9. Use `improve-codebase-architecture` only after behavior is correct, so refactoring is evidence-driven.

## Update policy

Do not run blind bulk updates. Before `npx skills update`, inspect the upstream change history for the selected skill sources. If a skill changes behavior materially, update this document or an ADR and re-run the repository verification suite.
