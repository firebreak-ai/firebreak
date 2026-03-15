# Task 001: Create the Index Document

**Output file**: `.claude/docs/context-assets.md`
**Dependencies**: None (wave 1 — this establishes the canonical principles all other files reference)

## Context

This is the core content document for the context asset authoring framework. It loads on demand when the agent is authoring any type of context asset. Both triggers (rule and skill) point here. All leaf documents must be consistent with the principles defined here.

Read `ai-docs/mvp-000/plan.md` sections: "Core Principles", "A note on plan prose vs. authored content", and the index file description under "File descriptions > Content > 4."

## Output Specification

Create `.claude/docs/context-assets.md` with this structure:

### Section 1: Six Core Principles

Translate each principle from the plan into agent-compressed form. Follow these rules:

- Strip all research citations. The agent needs the rule, not the provenance.
- Strip all motivational framing and explanatory prose.
- Use imperative, direct-address instructions.
- Frame all instructions positively (the plan has already been revised to do this — follow its lead).
- Each instruction must be a single, verifiable constraint.

**Principle order** (for positional attention optimization):
1. The Necessity Test (position 1 — most important gate)
2. Progressive Disclosure
3. Separation of Concerns
4. Trust the Agent's Native Capabilities
5. Choose the Right Trigger and Content Strategy
6. Write for Agents, Not Humans (position 6 — end position, high attention)

For each principle, use a `##` heading and keep the content to the minimum that prevents authoring mistakes. Refer to the plan for the full principle descriptions, but compress aggressively.

**Specific content requirements per principle:**

- **Necessity Test**: Include the test question ("If this instruction were removed..."), the filter list (4 items), the shared budget framing (one sentence — no citations), and the security carve-out (security-defensive instructions may pass the test even when they seem unnecessary).
- **Progressive Disclosure**: Router → Index → Leaf pattern. Three tiers with their roles. Keep it to the structural pattern — the routing table below demonstrates it in action.
- **Separation of Concerns**: Four bullets from the plan (triggers/content distinction, one file one concern, inline vs. extract, conflicts as bugs). Drop the "Context assets are a software system" preamble.
- **Trust Native Capabilities**: Good/bad example pair. "Include only what the agent can't figure out alone" closing line.
- **Right Trigger and Content Strategy**: Trigger types table (5 rows). Content strategies table (3 rows). Four key considerations. This is the densest principle — use tables for scannability.
- **Write for Agents**: Six bullets (start with first instruction, state rules directly, default to imperatives, direct address, frame positively, one instruction one constraint). Review heuristic question.

### Section 2: Routing Table

Use this exact table:

```
| When you are... | Read |
|-----------------|------|
| Writing or modifying a CLAUDE.md file | `context-assets/claude-md.md` |
| Writing or modifying a rule | `context-assets/rules.md` |
| Writing or modifying a skill | `context-assets/skills.md` |
| Writing or modifying a hook | `context-assets/hooks.md` |
| Writing or modifying an agent | `context-assets/agents.md` |
| Writing or modifying a docs/ file (index or leaf) | `context-assets/referenced-docs.md` |
```

### Section 3: Instruction Writing Checklist

Place at document bottom (U-shaped attention — high recall position). Four items, phrased differently from the Principle 5 bullets to avoid literal repetition:

- **Compress**: fewest tokens that reliably produce the desired behavior
- **Positive**: state what to do, not what to avoid
- **Atomic**: each instruction is independently verifiable
- **Show when telling fails**: 2-3 examples for style/format/tone; declarative rules for unambiguous constraints

## Verification Criteria

After writing, count the discrete imperative instructions in the document. Target: 35-42. If significantly over, compress further. If significantly under, check that all principle content from the plan is represented.

Verify the document follows its own rules:
- [ ] Starts with the first principle — no preamble, no "this document describes..."
- [ ] All instructions use positive framing
- [ ] Each instruction is a single verifiable constraint (no compound rules)
- [ ] No research citations or paper references
- [ ] No motivational framing ("it's important to...", "best practice is to...")
- [ ] Direct address throughout ("Use X" not "Authors should use X")
