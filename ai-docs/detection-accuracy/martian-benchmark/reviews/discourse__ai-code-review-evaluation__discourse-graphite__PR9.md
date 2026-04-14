# Code Review: FEATURE: Localization fallbacks (server-side)

**PR**: [discourse-graphite#9](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/9)
**Instance**: discourse__ai-code-review-evaluation__discourse-graphite__PR9
**Preset**: behavioral-only
**Date**: 2026-04-13

## Intent Register

### Intent Claims

1. **IC-01**: The PR replaces Rails' built-in `config.i18n.fallbacks = true` with a custom `FallbackLocaleList` that provides a deterministic fallback chain: user locale -> site default locale -> English.
2. **IC-02**: The `FallbackLocaleList` class inherits from `Hash` and overrides `[]` to compute the fallback chain dynamically on every access, reflecting the current `SiteSetting.default_locale`.
3. **IC-03**: `FallbackLocaleList#ensure_loaded!` eagerly loads all locales in the fallback chain for the current `I18n.locale` by calling `I18n.ensure_loaded!` on each.
4. **IC-04**: A new `ensure_loaded!(locale)` method is added to the translate accelerator (freedom patch on I18n) to lazily load a locale if not already in `@loaded_locales`.
5. **IC-05**: The pluralization backend inclusion (previously in `config/initializers/pluralization.rb`) is consolidated into the new `config/initializers/i18n.rb`.
6. **IC-06**: `config.i18n.fallbacks = true` is removed from three environment configs (production, cloud66/production, profile) since fallbacks are now configured centrally in the initializer.
7. **IC-07**: `I18n.fallbacks.ensure_loaded!` is called at the end of `set_locale` in `ApplicationController`, ensuring fallback locales are preloaded on every request after the locale is determined.
8. **IC-08**: The initializer has an explicit ordering dependency (`# order: after 02-freedom_patches.rb`) because the fallback setup requires the translate accelerator freedom patch to be loaded first.

### Intent Diagram

```mermaid
graph TD
    subgraph Request Path
        AC[ApplicationController<br>set_locale] -->|calls| EL[FallbackLocaleList<br>ensure_loaded!]
    end

    subgraph I18n Configuration
        INIT[config/initializers/i18n.rb] -->|includes| PLUR[Pluralization Backend]
        INIT -->|includes| FB[Fallbacks Backend]
        INIT -->|sets| FLL[FallbackLocaleList]
        FLL -->|overrides []| CHAIN["[locale, site_default, :en]"]
    end

    subgraph Freedom Patches
        TA[translate_accelerator.rb] -->|defines| ELM[ensure_loaded! method]
    end

    EL -->|iterates chain| ELM
    ELM -->|loads locale if missing| LL[@loaded_locales]

    subgraph Removed
        PROD[production.rb] -.-|removed| OLD["config.i18n.fallbacks = true"]
        CLOUD[cloud66/production.rb] -.-|removed| OLD
        PROF[profile.rb] -.-|removed| OLD
        PLURF[pluralization.rb] -.-|deleted| OLD2[separate initializer]
    end
```

## Verified Findings

### F-01 (S-02) — Missing nil/blank guard on `SiteSetting.default_locale.to_sym`

| Field | Value |
|-------|-------|
| Location | `config/initializers/i18n.rb`, `FallbackLocaleList#[]` |
| Type | behavioral |
| Severity | major |
| Origin | introduced |
| Detection source | checklist |
| Pattern | zero-value-sentinel |
| Confidence | 10.0 |

**Current behavior**: `SiteSetting.default_locale.to_sym` is called with no guard against nil or blank return values. If `SiteSetting.default_locale` returns `nil`, `.to_sym` raises `NoMethodError` on every request via the `set_locale` -> `ensure_loaded!` -> `self[I18n.locale]` call path. If it returns `""` (empty string), `.to_sym` produces `:"" ` (an empty symbol) which is non-nil and passes through `.compact` unfiltered, silently inserting an invalid locale into the fallback chain. `I18n.ensure_loaded!` is then called with `:"" `, a locale that matches no translation files, producing no translations for that fallback slot with no error raised.

**Expected behavior**: Guard `SiteSetting.default_locale` against blank values before calling `.to_sym` so that blank/nil collapses to nil and `.compact` can remove it, e.g. `SiteSetting.default_locale.presence&.to_sym`.

**Evidence**: Line 82 of new file: `[locale, SiteSetting.default_locale.to_sym, :en].uniq.compact`. The `.to_sym` call is unconditional. On nil input, Ruby raises `NoMethodError: undefined method 'to_sym' for nil:NilClass`. On empty string, `"".to_sym` produces `:"" ` which is non-nil. Three independent detectors (G1, G3, G4) identified this independently.

---

### F-02 (S-07) — Non-request callers of `translate` bypass fallback locale loading

| Field | Value |
|-------|-------|
| Location | `lib/freedom_patches/translate_accelerator.rb` + `config/initializers/i18n.rb` |
| Type | behavioral |
| Severity | major |
| Origin | introduced |
| Detection source | structural-target |
| Pattern | dual-path-verification |
| Confidence | 8.0 |

**Current behavior**: The `translate` method in `translate_accelerator.rb` inline-guards locale loading with `load_locale(config.locale) unless @loaded_locales.include?(config.locale)`, loading only the primary locale. The full fallback chain loading (`I18n.fallbacks.ensure_loaded!`) is only called from `set_locale` in `ApplicationController`, which is a web-request-only hook. Non-request callers of `translate` (background jobs, rake tasks, Rails console) receive no fallback locale coverage. When the I18n fallback backend attempts to look up translations in a fallback locale under these callers, the fallback locale's translations have not been loaded.

**Expected behavior**: Fallback locales should be loaded for all callers of `translate`, not only web requests. Either `translate` should trigger fallback loading, or `ensure_loaded!` should be called from a more general hook point.

**Evidence**: Line 112 of diff shows `translate` loads only `config.locale`. Line 10 of `application_controller.rb` change shows `I18n.fallbacks.ensure_loaded!` is only called from `set_locale`. No other caller of `ensure_loaded!` exists in the diff.

---

## Findings Summary

| ID | Type | Severity | Description |
|----|------|----------|-------------|
| F-01 | behavioral | major | Missing nil/blank guard on `SiteSetting.default_locale.to_sym` — nil raises NoMethodError, empty string inserts invalid locale |
| F-02 | behavioral | major | Non-request callers of `translate` bypass `set_locale` and receive no fallback locale loading |

**Totals**: 2 verified findings, 3 rejections (1 nit + 2 rejected), 4 filtered (out-of-charter)

## Filtered Findings

| Sighting | Type | Severity | Reason | Score |
|----------|------|----------|--------|-------|
| S-03 | structural | minor | out-of-charter (structural type, behavioral-only preset) | 8.0 |
| S-04 | fragile | minor | out-of-charter (fragile type, behavioral-only preset) | 7.0 |
| S-06 | structural | minor | out-of-charter (structural type, behavioral-only preset) | 7.0 |
| S-09 | structural | minor | out-of-charter (structural type, behavioral-only preset) | 7.0 |

## Retrospective

### Sighting Counts

| Metric | Count |
|--------|-------|
| Total sightings generated | 12 |
| After deduplication | 9 |
| Verified findings (at termination) | 6 |
| Verified findings (after charter filter) | 2 |
| Rejections | 3 |
| Nits | 1 |
| Filtered (out-of-charter) | 4 |

**By detection source:**
| Source | Sightings | Findings |
|--------|-----------|----------|
| checklist | 6 | 1 (F-01) |
| structural-target | 3 | 1 (F-02) |
| intent | 3 | 0 (all filtered) |

**Structural sub-categorization (pre-filter):** dead conditional guard (S-03), semantic drift (S-09), implicit ordering dependency (S-06)

### Verification Rounds

- **Round 1**: 5 agents spawned (G1-G4 + IPT). 12 sightings produced, deduplicated to 9. 6 verified, 3 rejected. After charter filter: 2 findings retained (behavioral type only). 4 findings filtered as out-of-charter (structural/fragile types under behavioral-only preset).
- **Round 2**: Not executed. Eligible agents: G1, G3, G4 (all produced verified findings above info). Rationale for termination: the entire code surface (~50 lines across 7 files) was exhaustively covered in Round 1 with no unexamined code. Respawning agents on the identical payload would reproduce the same observations. Hard cap not reached (1/5 rounds).

### Scope Assessment

- **Files in scope**: 7 (1 new, 1 deleted, 5 modified)
- **Lines changed**: ~50 (24 added in new file, 5 added in translate_accelerator, 2 added in application_controller, ~15 removed across 3 env configs, 2 removed in deleted file)
- **Reviewable units**: 1 (single cohesive feature)

### Context Health

- Round count: 1
- Sightings-per-round: 12 (Round 1)
- Rejection rate: 3/9 = 33% (Round 1)
- Hard cap reached: No

### Tool Usage

- Linter output: N/A (no project-native linters available — isolated diff review)
- Code navigation: diff-only context, no repository browsing

### Finding Quality

- False positive rate: TBD (pending user review)
- False negative signals: TBD (pending user review)
- Origin breakdown: all findings marked `introduced` (new code in this PR)

### Intent Register

- Claims extracted: 8 (from diff content, PR title, and code structure)
- Claims sourced from: PR title (1), code comments (2), code structure/behavior (5)
- Findings attributed to intent comparison: 0 after charter filter (IPT sightings S-04, S-06 were filtered as out-of-charter)
- Intent claims invalidated: 0

### Per-Group Metrics

| Agent | Files reported / in scope | Sightings | Survival rate | Phase |
|-------|--------------------------|-----------|---------------|-------|
| G1 (value-abstraction) | 7/7 | 2 | 1/2 = 50% (1 merged into F-01, 1 nit) | Enumeration |
| G2 (dead-code) | 7/7 | 1 | 0/1 = 0% (merged into S-03, filtered out-of-charter) | Enumeration |
| G3 (signal-loss) | 7/7 | 1 | 1/1 = 100% (merged into F-01) | Enumeration |
| G4 (behavioral-drift) | 7/7 | 4 | 1/4 = 25% (G4-S-01 → F-02; others merged/filtered) | Enumeration |
| IPT (intent-path-tracer) | 7/7 | 4 | 0/4 = 0% (2 filtered, 2 rejected) | Enumeration |

### Deduplication Metrics

- Merge count: 2
- Merged pairs: {G1-S-02, G3-S-01, G4-S-02} → S-02; {G2-S-01, G4-S-04} → S-03
- Pre-dedup sighting count: 12
- Post-dedup sighting count: 9

### Instruction Trace

- Per-agent instruction files: agent definition files loaded at spawn time (t1-value-abstraction-detector, t1-dead-code-detector, t1-signal-loss-detector, t1-behavioral-drift-detector, intent-path-tracer, sighting-deduplicator, code-review-challenger)
- Prompt composition: code payload (~50 lines) + intent register (8 claims) + detection targets per group
- Agents spawned: 5 detectors + 1 deduplicator + 2 challengers = 8 total

