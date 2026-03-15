## Feature Threat Model Structure

Produce `ai-docs/<feature-name>/<feature-name>-threat-model.md` with these eight sections:

**1. Assets** — List what the feature protects or exposes: data types, credentials, sessions, configuration, secrets. Be specific (e.g., "user session tokens stored in Redis" not "user data").

**2. Threat actors** — Identify who might attack: unauthenticated external users, authenticated users escalating privilege, malicious insiders, automated bots, compromised third-party services.

**3. Trust boundaries** — Map where trust levels change: client/server boundary, internal/external service calls, user/admin separation, service-to-service with different credential scopes.

**4. Data flows** — Trace how data moves across each trust boundary identified above. Include the direction, data type, and authentication mechanism at each crossing.

**5. Threats** — Apply STRIDE to each data flow crossing a trust boundary (see STRIDE reference below). For each threat, record: STRIDE category, affected component, specific attack scenario, likelihood (low/medium/high), and impact (low/medium/high).

**6. Mitigations** — For each identified threat, state the control: existing controls already in place, proposed new controls, or "none — see residual risks." Link mitigations to threats by referencing the threat's STRIDE category and component.

**7. Residual risks** — List threats accepted without full mitigation. For each: state the threat, explain why it is accepted (cost/benefit, compensating control, low probability), and identify the risk owner. Do not leave this section empty without confirming there are genuinely no residual risks.

**8. Proposed project model updates** — List specific additions, removals, or modifications to `ai-docs/threat-model.md`, with rationale for each change. Do not apply changes to the project model until the user reviews and approves this section. If the project model does not yet exist, this section is the seed content for creating it.

---

## STRIDE Reference

Apply each category to every data flow crossing a trust boundary. A single data flow may yield multiple threats across categories — do not stop at the first match.

| Category | Question to ask | Example | Typical mitigations |
|----------|----------------|---------|---------------------|
| **Spoofing** | Can an attacker impersonate a legitimate entity? | Forged session token; API caller claiming an identity it does not own | Strong authentication; token validation; mutual TLS |
| **Tampering** | Can data be modified in transit or at rest? | Request body altered between client and server; database record modified by unauthorized user | TLS in transit; integrity checks; input validation; authorization on writes |
| **Repudiation** | Can actions be performed without accountability? | No audit log for privileged operations; log entries deletable by the actor being logged | Immutable audit logs; tamper-evident logging; log forwarding to separate store |
| **Information disclosure** | Can sensitive data leak? | Error messages exposing stack traces; API response including fields for a different user | Minimal error detail to clients; authorization on reads; field-level access control |
| **Denial of service** | Can availability be degraded? | Unauthenticated endpoint accepting unbounded input; missing rate limiting on expensive operation | Rate limiting; authentication before expensive operations; input size limits |
| **Elevation of privilege** | Can an attacker gain unauthorized access levels? | Horizontal: accessing another user's resources. Vertical: gaining admin from user role | Enforce authorization server-side; never trust client-supplied role claims |

---

## Modeling Process

1. Read `ai-docs/threat-model.md` if it exists. Understand the current asset inventory, existing trust boundaries, and known residual risks before analyzing the feature. If no project model exists, proceed — section 8 of the feature model will seed it.

2. Read the feature spec. Identify: new entry points, data the feature touches, trust boundaries it crosses or introduces, integrations with external services, changes to authentication or authorization logic.

3. Security agent leads the analysis. Invite Architect when the feature introduces new system boundaries or modifies existing ones — they contribute to sections 3 and 4 (trust boundaries and data flows).

4. For each feature component: enumerate assets, identify trust boundaries, trace data flows, apply all six STRIDE categories to each data flow that crosses a trust boundary. Work component by component — do not attempt STRIDE across the whole feature at once.

5. For each threat: assess likelihood (how easily exploited) and impact (what is compromised). Propose mitigations proportional to both.

6. Compare against the project model. Identify what the feature adds (new assets, new boundaries), modifies (changed severity of an existing threat, updated mitigation), or invalidates (removed component, retired trust boundary).

**Threat entry format** — Use a consistent format for each threat in section 5 to make the model scannable and comparable across features:

```
### [STRIDE category]: [Component] — [Brief scenario title]
- **Actor**: who initiates the attack
- **Attack**: how the attack is executed
- **Likelihood**: low | medium | high
- **Impact**: low | medium | high
- **Mitigation**: reference to section 6, or "none — residual risk"
```

Apply this format for every threat. If a data flow crossing a trust boundary yields no threats under a STRIDE category, note "none identified" — do not silently skip it.

---

## Project Model Maintenance

The project model (`ai-docs/threat-model.md`) reflects the current threat landscape across all features. Propose changes in the "Proposed project model updates" section of the feature threat model — never edit the project model directly during feature review.

For each proposed change, specify:
- **Type**: addition, modification, or removal
- **Target**: which section and item in the project model
- **Change**: the exact content to add, replace, or remove
- **Rationale**: why this feature requires the change

Changes are not limited to additions. A bug fix may lower a threat's severity. A refactored feature may remove a trust boundary or retire an asset. Apply the same rigor to removals and modifications as to additions — an outdated project model misleads future threat analysis.

The user reviews and approves proposed changes. Apply them to `ai-docs/threat-model.md` only after explicit approval.

When the project model does not yet exist, the first feature's section 8 creates it. Structure the initial project model with the same section headings used across feature models: assets, threat actors, trust boundaries, threats, mitigations, residual risks.

---

## Sensitivity

Threat models document assets, attack surfaces, and residual risks. This information serves as an attacker's roadmap if exposed.

Exclude all threat model files from version control. Add this rule to `.gitignore`:

```
*threat-model*
```

Naming convention (deterministic — enables the gitignore rule to match):
- Project-level: `threat-model.md` at `ai-docs/threat-model.md`
- Feature-level: `<feature-name>-threat-model.md` at `ai-docs/<feature-name>/<feature-name>-threat-model.md`

Never commit a threat model file. If one appears in `git status`, verify `.gitignore` contains the `*threat-model*` rule and that the file is not already tracked. A tracked file requires `git rm --cached` to untrack it; adding it to `.gitignore` alone is insufficient.
