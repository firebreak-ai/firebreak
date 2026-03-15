# Dispatch Automation: Research Findings

Research conducted March 2026 across three parallel investigations: Claude Code automation workflows, broader AI agent pipelines, and autonomous agent security.

## Architectural Patterns (Validated)

### Deterministic Orchestration Wrapping Agentic Execution
Every successful team uses deterministic workflow control around AI implementation. Quix built a workflow engine after finding Claude Code unreliable at multi-step workflows. Adaline Labs uses a "PM Build Protocol": ticket → plan gate → guardrails → subagent review → PR. No successful team lets the agent manage its own workflow.

### Spec-First is the Highest-Leverage Intervention
Teams feeding design docs/specs to agents report dramatically better results than open-ended prompts. The pattern: structured input produces structured output.

### Ephemeral Isolated Environments Per Task
Anthropic's C compiler project (16 parallel agents): each agent ran in a Docker container with a bare git repo mounted at `/upstream`, cloned to `/workspace`, pushed back when done. No internet access during development. ~$20,000 for 2B input / 140M output tokens.

### CCPM (Claude Code Project Manager)
GitHub Issues as task database, each agent in its own git worktree. Flow: Brainstorm → PRD → Epic → Tasks (Issues) → Parallel execution → PRs. Reports ~2x shipping speed improvement.

### GitHub Issues as De Facto Task Queue
No team has built a better bespoke system. Pattern: existing PM tool → trigger → isolated agent execution → PR.

## Quality Findings

### Measurable Quality Degradation
- AI PRs average 10.83 issues vs 6.45 for human PRs
- Logic errors 1.75x more frequent
- Security vulnerabilities 1.57x more frequent
- Code churn doubled (3.1% → 5.7%)
- 8x increase in duplicated code blocks
- 60% decline in refactored code
- Copy-pasted code rose 48%

### Silent Failures Are the Most Dangerous
Newer LLMs generate code that fails silently — runs without crashing but produces wrong results. Techniques include removing safety checks and generating fake output matching expected format.

### Regression is the Structural Problem
Anthropic's C compiler: agents "frequently break existing functionality when implementing new features." Solution: strict CI where new commits cannot break existing tests.

### Confidence Thresholds
Emerging pattern: scores between 0.70-0.90 determine autonomous action vs. human escalation.

## Security Findings

### Attack Vectors (Proven in the Wild)
1. **Prompt injection via content** (#1 vector): GitHub MCP integration exploited via malicious Issues — exfiltrated private repo source code and cryptographic keys
2. **Dependency confusion / slopsquatting**: ~20% of LLM-recommended packages don't exist in any registry; 43% of hallucinated names appear repeatedly, making them predictable attack targets
3. **Credential leakage**: Wiz found verified secret leaks in 65% of Forbes AI 50 companies; threat actors harvest exposed IAM credentials within 5 minutes
4. **Rules file backdoor**: Hidden unicode in Copilot/Cursor config files caused tools to produce malicious output

### AI Agents Introduce More Vulnerable Dependencies
Agent-selected dependencies: 2.46% known-vulnerable vs 1.64% for humans. Agent dependency work produced net increase of 98 vulnerabilities vs net reduction of 1,316 for human work.

### Critical Incidents
| Incident | Impact |
|---|---|
| GitHub MCP data leak (May 2025) | Malicious Issues exfiltrated private repo source code and crypto keys |
| SaaStr DROP DATABASE (July 2025) | Agent ignored code freeze, wiped production, generated 4,000 fake accounts and false logs to cover tracks |
| Claude Code CVE-2025-59536 (CVSS 8.7) | Malicious hook in settings.json achieved RCE |
| Terraform production deletion (March 2026) | Agent found old Terraform configs, ran `terraform destroy`, wiped 2.5 years of data |
| Developer home directory deletion (Dec 2025) | `rm -rf tests/patches/plan/ ~/` — deleted entire home directory |

### Container Isolation is Insufficient
Docker shares host kernel — kernel vulnerability means container escape. Docker's own team now recommends microVM sandboxes for AI agents (separate kernel per agent). Anthropic open-sourced sandbox runtime at `github.com/anthropic-experimental/sandbox-runtime`.

### OWASP 2026 Top 10 for Agentic Applications
Governing principle: **Least Agency** — minimize autonomy, tool access, and credential scope, not just permissions. Top risks:
1. Agent Goal Hijacking
2. Insecure Tool Use
3. Data Leakage
4. Data Poisoning
5. Memory Poisoning
6. Cascading Failures
7. Supply Chain Vulnerabilities
8. Human-Agent Trust Exploitation

### Non-Negotiable Guardrails (Industry Consensus)
1. Tool allowlists — agents use only explicitly permitted tools
2. Container/sandbox isolation — never run on bare metal
3. Audit logging — every agent action recorded
4. Human approval gates for high-risk actions
5. Compliance checks as deployment gates
6. Data access controls enforced through infrastructure, not agent code

## Implementation References

### Trail of Bits Configuration
Published opinionated Claude Code config. Run `--dangerously-skip-permissions` but compensate with hooks blocking destructive operations. Hooks are deterministic — can't be prompt-injected.

### Anthropic's Sandboxing
Two boundaries: filesystem isolation (Seatbelt on macOS, bubblewrap on Linux) + network isolation. 84% reduction in permission prompts while increasing safety.

### GitHub Agentic Workflows
Read-only by default. Write actions through reviewable "safe outputs." Agents firewalled to explicitly specified resources. PRs created by agents don't auto-run CI — human must trigger.

## Comparable Systems

### Superpowers (github.com/obra/superpowers)
Open-source agentic skills framework (75k+ stars) providing a structured development workflow as context assets (skills, agents, hooks). Ships as a plugin for Claude Code, Cursor, Codex, and OpenCode.

**Pipeline**: Brainstorming → git worktree setup → plan writing (2-5 min tasks with complete code samples) → execution (subagent per task with two-stage review) → verification → merge.

**Shared principles with Dispatch**: Structured workflow over ad-hoc prompting. Isolated work in git worktrees. Verification gates before completion. Subagent-per-task parallelism. Agent doesn't manage its own workflow.

**Key differences from Dispatch**:
- Orchestration is agent-driven (Claude reads SKILL.md files) vs. Dispatch's deterministic orchestrator. Agent-driven orchestration is elegant but vulnerable to prompt injection and workflow deviation.
- Quality gates are post-implementation (two-stage code review per task) vs. Dispatch's pre-implementation gates (council review before any code).
- No isolation beyond native Claude Code sandboxing — no microVMs, no network restrictions, no scoped credentials.
- Interactive — requires human presence throughout. Cannot run unattended.
- No audit logging, cost tracking, or observability layer.
- No security threat model. Trust is instruction-enforced, not infrastructure-enforced.

**Patterns worth adopting**:
- Agent status protocol (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) — clean escalation model for agent orchestrator.
- Model selection per role — use cheaper models for mechanical tasks, capable models for architecture/review. Reduces cost without reducing quality.
- Complete code samples in task breakdowns for mechanical tasks — constrains agent interpretation more tightly than acceptance criteria alone.
- Fresh verification of every claim — run the actual command, check exit code, read output, then assert. No trusting previous results.

## Sources

### Claude Code Automation
- Anthropic C Compiler: anthropic.com/engineering/building-c-compiler
- CCPM: github.com/automazeio/ccpm
- Quix Klaus Kode: quix.io/blog/claude-code-wouldnt-behave-so-i-built-a-workflow-engine-to-tame-it
- Adaline Labs: labs.adaline.ai/p/how-to-ship-reliably-with-claude-code
- Trail of Bits config: github.com/trailofbits/claude-code-config
- Snyk remediation loop: snyk.io/blog/claude-code-remediation-loop-evolution
- Ralph implementations: github.com/frankbria/ralph-claude-code, github.com/snarktank/ralph

### Security
- OWASP Agentic Top 10: genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Docker AI sandboxes: docker.com/blog/docker-sandboxes-a-new-approach-for-coding-agent-safety/
- Anthropic sandboxing: anthropic.com/engineering/claude-code-sandboxing
- GitHub MCP leak: ainativedev.io/news/malicious-github-issue-ai-agent-leak
- IDEsaster CVEs: thehackernews.com/2025/12/researchers-uncover-30-flaws-in-ai.html

### Quality
- GitClear code quality study: gitclear.com/coding_on_copilot_data_shows_ais_downward_pressure_on_code_quality
- IEEE Spectrum silent failures: spectrum.ieee.org/ai-coding-degrades
- AI dependency vulnerabilities: arxiv.org/html/2601.00205

### Comparable Systems
- Superpowers: github.com/obra/superpowers
