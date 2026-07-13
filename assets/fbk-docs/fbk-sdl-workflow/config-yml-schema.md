Place `config.yml` at `.claude/automation/config.yml` in the project root.

## Fields

- `token_budget`: integer or null. Maximum token budget for the pipeline run. Default: null (no limit).
- `max_concurrent_agents`: integer. Maximum agents running simultaneously. Default: 1.
- `escalation_cap`: integer. Maximum escalation attempts per task before parking. Default: 2.
- `model`: string or object. As string: default model for all pipeline stages. As object: `default` key for the baseline model, plus per-stage keys overriding specific stages. Default: `"sonnet"`.

- `cross_model_review`: object. Configuration for cross-model review — a second-opinion review run against a different external model. Sending content to a third-party model requires operator opt-in. Fields:
  - `enabled`: boolean. Whether cross-model review runs. Default: false. Set to true to opt in; enabling sends the reviewed content (the document or diff and any loaded context) to the external third-party model.
  - `harness`: string. The external review harness to invoke. v1 supports only `codex`.
  - `model`: string. The external model identifier, e.g. `gpt-5.6-sol`.
  - `effort`: string. The effort level passed to the harness, e.g. `high`.

  Note: the `cross_model_review` block is read directly from the project's
  `.claude/automation/config.yml` by the `cross-review` runner; unlike the
  pipeline fields below, it is **not** subject to the spec-frontmatter layer.
  The opt-in is a project-level consent boundary for third-party egress, so it
  cannot be turned on (or off) by a per-run spec frontmatter override.

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
cross_model_review:
  enabled: true
  harness: codex
  model: gpt-5.6-sol
  effort: high
```
