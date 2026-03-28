Place `config.yml` at `.claude/automation/config.yml` in the project root.

## Fields

- `token_budget`: integer or null. Maximum token budget for the pipeline run. Default: null (no limit).
- `max_concurrent_agents`: integer. Maximum agents running simultaneously. Default: 1.
- `escalation_cap`: integer. Maximum escalation attempts per task before parking. Default: 2.
- `model`: string or object. As string: default model for all pipeline stages. As object: `default` key for the baseline model, plus per-stage keys overriding specific stages. Default: `"sonnet"`.

## Layering order

Configuration merges three layers with more-specific-wins precedence:

1. Hardcoded defaults (lowest priority)
2. Project `config.yml`
3. Spec YAML frontmatter (highest priority)

Each layer overrides the previous for any key it defines.

## Example

```yaml
token_budget: 10000
max_concurrent_agents: 3
escalation_cap: 4
model:
  default: sonnet
  reviewing: opus
  implementing: sonnet
```
