# Consensus Failure

This leaf is loaded when Round 1 of Phase 3 ends without consensus. It contains both the decision protocol (always applied first to break the deadlock by task type) and the conflict-resolution rules (applied if the decision protocol surfaces unresolved conflict between specific agents). Both sections live in the same file under a single dispatch from the SKILL, eliminating leaf-to-leaf chaining.

## Decision Protocol

When agents disagree, use the appropriate decision mechanism based on task type.

### Task Classification

Before Phase 3 discussion, classify the task:

| Task Type | Description | Examples |
|-----------|-------------|----------|
| **Reasoning** | Requires judgment, tradeoffs, or architectural decisions | "Should we use X or Y?", "How should we structure this?", "What's the best approach?" |
| **Knowledge** | Has a factual answer discoverable through research | "What does the API return?", "How does framework X handle Y?", "What are the requirements?" |

### Protocol by Task Type

**For Reasoning Tasks → Weighted Voting**

After Round 1 discussion, if no clear consensus:
1. Each agent votes on the recommendation
2. Votes are weighted by domain relevance:
   - **2x weight** when voting on their specialty:
     - Architect: architecture/structure decisions
     - Builder: implementation complexity decisions
     - Security: security-related decisions
     - Advocate: user experience decisions
     - Analyst: performance/metrics decisions
     - Guardian: quality/testing decisions
   - **1x weight** otherwise
3. Tally weighted votes; majority wins
4. Tie-breaker: Builder + Advocate (Complexity Watchdogs) decide jointly

**For Knowledge Tasks → Evidence-Based Consensus**

1. Agents research and share findings with citations
2. Seek convergence on factual answer
3. If sources conflict, note the conflict and recommend further investigation
4. No voting needed—evidence determines outcome

### Decision Documentation

Add to Phase 5 output when decision protocol was used:

```markdown
## Decision Protocol Used
**Task Type**: [Reasoning/Knowledge]
**Method**: [Weighted Voting/Evidence Consensus]

[For Voting only:]
| Agent | Vote | Weight | Weighted |
|-------|------|--------|----------|
| Architect | [Choice] | [1x/2x] | [1/2] |
| ... | ... | ... | ... |

**Result**: [Recommendation] with [X] weighted votes
```

## Conflict Resolution

When agents disagree and voting doesn't resolve the conflict, use these resolution rules.

### Resolution by Conflict Type

**1. Technical Disagreement** (e.g., Architect vs Builder on approach)
- **Resolution**: Builder has tie-breaking authority on implementation complexity
- **Rationale**: Implementation cost is the most concrete, measurable factor
- **Action**: Document dissent, proceed with Builder's recommendation

**2. Security vs Usability** (e.g., Security vs Advocate on friction)
- **Resolution**: Depends on risk level (Security agent provides assessment)
  - **Critical/High risk**: Security recommendation takes precedence
  - **Medium/Low risk**: Advocate recommendation takes precedence
- **Action**: Document the risk-benefit tradeoff explicitly

**3. Quality vs Speed** (e.g., Guardian vs Builder on testing depth)
- **Resolution**: Guardian has authority on critical paths; Builder on non-critical
- **Critical path defined as**: User-facing, security-sensitive, or data-modifying
- **Action**: Document which paths are critical and why

**4. Feature Scope** (e.g., Advocate flags complexity creep)
- **Resolution**: Advocate has tie-breaking authority (Complexity Watchdog role)
- **Rationale**: User burden compounds; implementation cost is one-time
- **Action**: Document removed scope for future consideration

### Deadlock Protocol

If no resolution after applying above rules:

1. **Orchestrator summarizes the deadlock clearly**
   - State the specific disagreement
   - Present both positions with supporting arguments
   - Explain why resolution rules don't apply

2. **Escalate to user**
   - Ask for decision input with clear options
   - Provide orchestrator's neutral summary of tradeoffs

3. **Document user decision**
   - Record in output which option was chosen and why
   - Note this as user-directed resolution

### Conflict Documentation

All conflicts MUST appear in the Dissenting Views section:

```markdown
## Dissenting Views
**[Agent A] vs [Agent B]**: [Issue summary]
- **[Agent A] position**: [Summary]
- **[Agent B] position**: [Summary]
- **Resolution**: [How resolved] per [rule applied]
- **Outcome**: [What was decided]
```
