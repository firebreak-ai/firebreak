# Task 011: Create README.md

**Output file**: `README.md` (project root)
**Dependencies**: 001 (should reference the framework accurately)

## Context

README.md is the one **human-facing** file in the project. It explains the project to developers browsing the repo. Unlike all other files, this is written for humans, not agents. The principles about "Write for Agents" do not apply here — but the principles about compression and necessity still do (even human readers benefit from concise documentation).

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 11."

## Output Specification

Create `README.md` at the project root covering:

### Content sections

1. **What this is** (1-2 paragraphs)
   - A framework for writing effective context assets for AI coding agents (Claude Code, etc.)
   - The core problem: monolithic instruction files hurt agent performance. Progressive disclosure helps.
   - This project provides authoring guidelines that teach agents how to create well-structured context assets.

2. **The progressive disclosure concept** (brief)
   - Router → Index → Leaf hierarchy
   - Agents load only what's relevant, not everything upfront
   - Brief visual (the three-tier diagram from the plan)

3. **Graduated adoption path**
   - Start simple: apply the Necessity Test to your existing CLAUDE.md
   - Next step: split by concern — move topic-specific rules to `.claude/rules/` with `paths:` scoping
   - Full framework: add routing tables when you have enough content to justify the index + leaf pattern
   - Emphasize: a 5-line CLAUDE.md that passes the Necessity Test beats a 500-line monolith

4. **Security note**
   - Review `.claude/` directories in repos you didn't author — instruction files are a prompt injection vector
   - Review `.claude/` changes in PRs with the same scrutiny as code changes
   - Keep this to 2-3 sentences — visible without being alarmist

5. **Empirical basis** (brief)
   - Reference the key research without turning this into an academic paper
   - Link to `research.md` for the full analysis
   - Key points: context pollution is measurable, compression helps, progressive disclosure is the recommended approach

### Scope boundaries

This file covers human orientation only. Leave these to other files:
- Installation instructions (there's nothing to install — these are markdown files)
- API documentation
- Detailed authoring rules (those live in `.claude/docs/`)
- Agent-targeted instructions of any kind

## Verification Criteria

- [ ] Target audience is explicitly human developers (not agents) — clear prose, explanatory where helpful
- [ ] Covers: what it is, progressive disclosure, adoption path, security, empirical basis
- [ ] Security note is present and visible (not buried)
- [ ] Graduated adoption path starts simple (Necessity Test on existing CLAUDE.md)
- [ ] Does not duplicate detailed authoring guidance from the docs
- [ ] Links to `research.md` for full analysis
