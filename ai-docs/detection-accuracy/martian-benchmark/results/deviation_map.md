# Martian Benchmark Deviation Map

**Firebreak version**: v0.3.5
**Judge**: consensus (3x Opus sub-agents, majority vote)
**Date**: 2026-04-09
**Threshold**: minor+

## Aggregate Summary

| Metric | Value |
|--------|-------|
| PRs evaluated | 50 |
| Golden comments | 136 |
| Firebreak findings | 452 |
| True positives | 93 |
| False positives | 360 |
| False negatives | 43 |
| **Precision** | **20.5%** |
| **Recall** | **68.4%** |
| **F1** | **31.6%** |

## Recall by Golden Severity

| Severity | TP | FN | Recall |
|----------|----|----|--------|
| Critical | 8 | 1 | 88.9% |
| High | 28 | 13 | 68.3% |
| Medium | 33 | 14 | 70.2% |
| Low | 24 | 15 | 61.5% |

## False Positive Breakdown

### By Finding Type

| Type | Count | % of FPs |
|------|-------|----------|
| behavioral | 160 | 44.4% |
| structural | 86 | 23.9% |
| test-integrity | 78 | 21.7% |
| fragile | 36 | 10.0% |

### By Finding Severity

| Severity | Count | % of FPs |
|----------|-------|----------|
| minor | 200 | 55.6% |
| major | 137 | 38.1% |
| critical | 16 | 4.4% |
| info | 7 | 1.9% |

## False Negative Breakdown

### By Golden Severity

| Severity | Count | % of FNs |
|----------|-------|----------|
| Critical | 1 | 2.3% |
| High | 13 | 30.2% |
| Medium | 14 | 32.6% |
| Low | 15 | 34.9% |

### By Issue Category (auto-classified)

| Category | Count | % of FNs |
|----------|-------|----------|
| api-misuse | 7 | 16.3% |
| data-integrity | 5 | 11.6% |
| style | 5 | 11.6% |
| logic-error | 4 | 9.3% |
| race-condition | 4 | 9.3% |
| type-error | 4 | 9.3% |
| other | 3 | 7.0% |
| null-safety | 3 | 7.0% |
| naming | 2 | 4.7% |
| security | 2 | 4.7% |
| test-quality | 2 | 4.7% |
| error-handling | 1 | 2.3% |
| observability | 1 | 2.3% |

## Per-Repo Summary

| Repo | PRs | Golden | Findings | TP | FP | FN | P | R | F1 |
|------|-----|--------|----------|----|----|----|---|---|---|
| cal_dot_com | 10 | 31 | 111 | 25 | 87 | 6 | 22.3% | 80.6% | 34.9% |
| discourse | 10 | 28 | 92 | 19 | 73 | 9 | 20.7% | 67.9% | 31.7% |
| grafana | 10 | 22 | 77 | 13 | 64 | 9 | 16.9% | 59.1% | 26.3% |
| keycloak | 10 | 24 | 74 | 16 | 58 | 8 | 21.6% | 66.7% | 32.6% |
| sentry | 10 | 31 | 98 | 20 | 78 | 11 | 20.4% | 64.5% | 31.0% |

---

## Per-PR Deviation Detail

### cal_dot_com__calcom__cal.com__PR8087
**Async import of the appStore packages** — [https://github.com/calcom/cal.com/pull/8087](https://github.com/calcom/cal.com/pull/8087)
Golden: 2 | Findings: 7 | TP: 1 | FP: 6 | FN: 1 | P=14% R=50% F1=22%

**True Positives:**
- G2 (Critical) → F-01 (behavioral/critical)
  Golden: The code uses forEach with async callbacks, which causes asynchronous operations (e.g., calendar/video event deletions, ...
  Finding: forEach-async-discard in vital/reschedule.ts

**False Negatives (missed golden):**
- G1 (Low) [error-handling]: Consider adding try-catch around the await to handle import failures gracefully

**False Positives (unmatched findings):**
- F-02 (behavioral/critical): forEach-async-discard in wipemycalother/reschedule.ts
- F-03 (behavioral/critical): forEach-async-discard in bookings.tsx
- F-04 (behavioral/major): Silent type drift — getCalendarCredentials stores Promise without await
- F-05 (structural/minor): Composition opacity — return type unchanged despite Promise property
- F-06 (structural/minor): Eager parallel loading — import() fires at eval time, not on access
- F-07 (fragile/minor): Dual key derivation — dirName vs type.split("_").join("")

---

### cal_dot_com__calcom__cal.com__PR10600
**feat: 2fa backup codes** — [https://github.com/calcom/cal.com/pull/10600](https://github.com/calcom/cal.com/pull/10600)
Golden: 4 | Findings: 13 | TP: 2 | FP: 11 | FN: 2 | P=15% R=50% F1=24%

**True Positives:**
- G2 (Low) → F-10 (behavioral/major)
  Golden: Error message mentions 'backup code login' but this is a disable endpoint, not login
  Finding: Exhausted codes return wrong error (disable)
- G4 (High) → F-09 (behavioral/major)
  Golden: Because backupCodes are decrypted and mutated in memory before being written back, two concurrent login requests using t...
  Finding: TOCTOU race on backup code invalidation

**False Negatives (missed golden):**
- G1 (Low) [naming]: The exported function TwoFactor handles backup codes and is in BackupCode.tsx. Inconsistent naming.
- G3 (Medium) [data-integrity]: Backup code validation is case-sensitive due to the use of indexOf(). This causes validation to fail if a user enters uppercase hex characters, as bac...

**False Positives (unmatched findings):**
- F-01 (behavioral/major): Missing encryption key guard in setup.ts
- F-02 (behavioral/major): Exhausted codes return wrong error (next-auth)
- F-03 (behavioral/minor): Blob URL not revoked on modal close
- F-04 (test-integrity/major): Non-enforcing 2FA switch assertion
- F-05 (test-integrity/major): No e2e tests for backup code auth paths
- F-06 (structural/minor): Backup code length as bare literals
- F-07 (structural/minor): Duplicated verification logic
- F-08 (behavioral/minor): Clipboard write not awaited
- F-11 (behavioral/minor): Missing .trim() on backup code input
- F-12 (behavioral/major): Cancel doesn't reset twoFactorLostAccess
- F-13 (behavioral/minor): Escape bypasses resetState in enable modal

---

### cal_dot_com__calcom__cal.com__PR10967
**fix: handle collective multiple host on destinationCalendar** — [https://github.com/calcom/cal.com/pull/10967](https://github.com/calcom/cal.com/pull/10967)
Golden: 5 | Findings: 13 | TP: 3 | FP: 10 | FN: 2 | P=23% R=60% F1=33%

**True Positives:**
- G1 (High) → F-03 (behavioral/critical)
  Golden: Potential null reference if mainHostDestinationCalendar is undefined if evt.destinationCalendar is null or an empty arra...
  Finding: EventManager null dereference on mainHostDestinationCalendar.integration
- G3 (High) → F-01 (behavioral/critical)
  Golden: Logic error: when externalCalendarId is provided, you're searching for a calendar where externalId === externalCalendarI...
  Finding: Google Calendar updateEvent tautological .find() — falsy externalCalendarId used as search value
- G4 (Medium) → F-08 (behavioral/major)
  Golden: Logic inversion in organization creation: The slug property is now conditionally set when IS_TEAM_BILLING_ENABLED is tru...
  Finding: Organization create handler inverted slug/requestedSlug logic

**False Negatives (missed golden):**
- G2 (Low) [style]: The optional chaining on mainHostDestinationCalendar?.integration is redundant since you already check mainHostDestinationCalendar in the ternary cond...
- G5 (Low) [api-misuse]: The Calendar interface now requires createEvent(event, credentialId), but some implementations (e.g., Lark/Office365) still declare createEvent(event)...

**False Positives (unmatched findings):**
- F-02 (behavioral/critical): Google Calendar deleteEvent tautological .find() — same pattern as F-01
- F-04 (behavioral/major): loadUsers removes organization select from Prisma query
- F-05 (behavioral/major): evt.destinationCalendar?.push silently no-ops when base is null
- F-10 (behavioral/major): updateAllCalendarEvents missing credential guard before updateEvent
- F-06 (behavioral/minor): console.error removed from updateAllCalendarEvents error handler
- F-07 (structural/minor): Duplicated credential-fetch-from-DB logic across two methods
- F-11 (structural/minor): Asymmetric externalId propagation in createAllCalendarEvents
- F-12 (behavioral/minor): requestReschedule missing user destinationCalendar fallback
- F-13 (behavioral/minor): Dropped video credentialId in result mapping
- F-09 (behavioral/info): Booking DB write connects only destinationCalendar[0]

---

### cal_dot_com__calcom__cal.com__PR22345
**feat: convert InsightsBookingService to use Prisma.sql raw queries** — [https://github.com/calcom/cal.com/pull/22345](https://github.com/calcom/cal.com/pull/22345)
Golden: 2 | Findings: 2 | TP: 1 | FP: 1 | FN: 1 | P=50% R=50% F1=50%

**True Positives:**
- G1 (Low) → F-01 (structural/minor)
  Golden: In getBaseConditions(), the else if (filterConditions) and final else branches are unreachable. This is because getAutho...
  Finding: Dead conditional guards in `getBaseConditions`

**False Negatives (missed golden):**
- G2 (Medium) [style]: Fetching userIdsFromOrg only when teamsFromOrg.length > 0 can exclude org-level members for orgs without child teams; consider deriving from teamIds (...

**False Positives (unmatched findings):**
- F-02 (test-integrity/major): Caching tests removed while caching logic remains

---

### cal_dot_com__calcom__cal.com__PR7232
**Comprehensive workflow reminder management for booking lifecycle events** — [https://github.com/calcom/cal.com/pull/7232](https://github.com/calcom/cal.com/pull/7232)
Golden: 2 | Findings: 11 | TP: 2 | FP: 9 | FN: 0 | P=18% R=100% F1=31%

**True Positives:**
- G1 (Medium) → F-04 (structural/major)
  Golden: Asynchronous functions deleteScheduledEmailReminder and deleteScheduledSMSReminder are called without await inside forEa...
  Finding: `forEach(async ...)` fire-and-forget in `workflows.tsx`
- G2 (High) → F-01 (behavioral/critical)
  Golden: When immediateDelete is true, the deleteScheduledEmailReminder function cancels the SendGrid email but fails to delete t...
  Finding: `immediateDelete` path missing DB cleanup — orphans WorkflowReminder records

**False Positives (unmatched findings):**
- F-02 (behavioral/major): Cron partial failure leaves stranded DB records (SendGrid cancelled but not deleted)
- F-03 (behavioral/major): Inconsistent `immediateDelete` between two rescheduling paths
- F-05 (behavioral/major): Missing SendGrid DELETE call in `immediateDelete` branch (regression)
- F-06 (behavioral/minor): No lower bound on `scheduledDate` in cron cancellation query
- F-07 (behavioral/minor): Cron cancel path also missing SendGrid DELETE
- F-08 (behavioral/minor): Cron doesn't guard against null `referenceId` before SendGrid call
- F-09 (behavioral/major): Fire-and-forget in `handleNewBooking.ts` rescheduling path
- F-10 (behavioral/major): Fire-and-forget regression in `bookings.tsx` — prior `await Promise.all` eliminated
- F-11 (behavioral/major): Fire-and-forget in `handleCancelBooking.ts` — cancellations removed from `prismaPromises`

---

### cal_dot_com__calcom__cal.com__PR8330
**Advanced date override handling and timezone compatibility improvements** — [https://github.com/calcom/cal.com/pull/8330](https://github.com/calcom/cal.com/pull/8330)
Golden: 2 | Findings: 16 | TP: 2 | FP: 14 | FN: 0 | P=12% R=100% F1=22%

**True Positives:**
- G1 (Medium) → F-03 (behavioral/critical)
  Golden: Incorrect end time calculation using slotStartTime instead of slotEndTime
  Finding: Copy-paste error — `end` computed from `slotStartTime`
- G2 (Medium) → F-02 (behavioral/critical)
  Golden: Using === for dayjs object comparison will always return false as it compares object references, not values. Use .isSame...
  Finding: Dead conditional guard — dayjs object identity `===`

**False Positives (unmatched findings):**
- F-01 (behavioral/critical): UTC offset sign inversion in date override day-matching
- F-04 (behavioral/major): Asymmetric interval boundary in date override check
- F-05 (behavioral/major): Inverted find() predicate in working-hours check
- F-06 (behavioral/major): UTC weekday vs organizer-local weekday mismatch
- F-07 (behavioral/major): Divergent organizerTimeZone between getSlots and checkIfIsAvailable
- F-08 (behavioral/major): Missing undefined guard on optional override.timeZone
- F-09 (test-integrity/minor): Bare string literals in test assertions
- F-10 (fragile/minor): String-keyed timezone lookup in test
- F-11 (behavioral/critical): Date override branch bypasses busy-time check
- F-12 (test-integrity/major): Test does not cover booking conflicts within date override windows
- F-13 (behavioral/major): Multi-override short-circuit via find()
- F-14 (structural/minor): Spread ordering allows override.timeZone overwrite
- F-15 (behavioral/major): dateOverrides and workingHours never wired to checkIfIsAvailable
- F-16 (behavioral/minor): DST boundary in offset calculation

---

### cal_dot_com__calcom__cal.com__PR11059
**OAuth credential sync and app integration enhancements** — [https://github.com/calcom/cal.com/pull/11059](https://github.com/calcom/cal.com/pull/11059)
Golden: 5 | Findings: 13 | TP: 5 | FP: 9 | FN: 0 | P=36% R=100% F1=53%

**True Positives:**
- G1 (High) → F-01 (behavioral/critical)
  Golden: The parseRefreshTokenResponse function incorrectly sets refresh_token to the hardcoded string 'refresh_token' when it's ...
  Finding: Sentinel refresh token persisted to credential store
- G2 (High) → F-02 (behavioral/major)
  Golden: Invalid Zod schema syntax. Computed property keys like [z.string().toString()] are not valid in Zod object schemas and w...
  Finding: Ineffective minimumTokenResponseSchema due to key collision
- G3 (High) → F-09 (behavioral/critical)
  Golden: parseRefreshTokenResponse returns a Zod safeParse result ({ success, data, error }), not the credential key object. Pers...
  Finding: Google Calendar stores SafeParseReturnType wrapper instead of token data
- G4 (High) → F-06 (behavioral/major)
  Golden: When APP_CREDENTIAL_SHARING_ENABLED and CALCOM_CREDENTIAL_SYNC_ENDPOINT are set, the refreshFunction helper returns the ...
  Finding: refreshOAuthTokens returns incompatible types across paths
- G5 (High) → F-06 (behavioral/major)
  Golden: When the sync endpoint path is used, res is a fetch Response and has no .data; res?.data will be undefined and token.acc...
  Finding: refreshOAuthTokens returns incompatible types across paths

**False Positives (unmatched findings):**
- F-03 (structural/minor): Dead conditional guard in Salesforce caller
- F-04 (behavioral/major): Office365 diagnostic logging removed
- F-05 (behavioral/minor): Timing-unsafe webhook secret comparison
- F-07 (behavioral/major): Zoho Bigin passes credentialId instead of userId
- F-08 (behavioral/minor): AES encryption key length not validated
- F-10 (behavioral/major): Webhook endpoint accepts all HTTP methods
- F-11 (behavioral/minor): Unhandled ZodError on malformed webhook body
- F-12 (structural/minor): Office365 dead guard in spread expression
- F-13 (behavioral/major): Salesforce unconditional token refresh at construction

---

### cal_dot_com__calcom__cal.com__PR14943
**SMS workflow reminder retry count tracking** — [https://github.com/calcom/cal.com/pull/14943](https://github.com/calcom/cal.com/pull/14943)
Golden: 2 | Findings: 7 | TP: 2 | FP: 5 | FN: 0 | P=29% R=100% F1=44%

**True Positives:**
- G1 (High) → F-06 (behavioral/major)
  Golden: Using retryCount: reminder.retryCount + 1 reads a possibly stale value and can lose increments under concurrency; consid...
  Finding: Non-atomic increment allows duplicate SMS and lost counts
- G2 (High) → F-01 (behavioral/major)
  Golden: The deletion logic in scheduleSMSReminders.ts incorrectly deletes non-SMS workflow reminders (e.g., Email, WhatsApp) tha...
  Finding: Missing method filter on retry-based deletion OR arm

**False Positives (unmatched findings):**
- F-02 (structural/minor): DB write in catch can swallow original error
- F-03 (structural/minor): Verbatim duplication of retryCount increment
- F-04 (structural/minor): Comment describes only one of two deletion conditions
- F-05 (fragile/minor): Fetch has no retryCount guard; relies on prior delete
- F-07 (structural/minor): Missing index on retryCount for recurring bulk delete

---

### cal_dot_com__calcom__cal.com__PR14740
**Add guest management functionality to existing bookings** — [https://github.com/calcom/cal.com/pull/14740](https://github.com/calcom/cal.com/pull/14740)
Golden: 5 | Findings: 19 | TP: 5 | FP: 14 | FN: 0 | P=26% R=100% F1=42%

**True Positives:**
- G1 (High) → F-09 (behavioral/minor)
  Golden: Case sensitivity bypass in email blacklist
  Finding: Case-insensitive blacklist bypass
- G2 (Critical) → F-01 (behavioral/critical)
  Golden: The logic for checking team admin/owner permissions is incorrect. This condition uses AND (&&) which requires both isTea...
  Finding: Authorization AND vs OR logic inversion
- G3 (Medium) → F-04 (behavioral/major)
  Golden: This calls the email sender with the original guests, so existing attendees included in the input will be treated as new...
  Finding: Raw vs filtered guest list in email dispatch
- G4 (Medium) → F-15 (behavioral/major)
  Golden: uniqueGuests filters out existing attendees and blacklisted emails but does not deduplicate duplicates within the input;...
  Finding: Case-sensitive attendee dedup allows duplicates
- G5 (Low) → F-05 (behavioral/minor)
  Golden: Starting with an array containing an empty string may cause validation issues. Consider starting with an empty array [] ...
  Finding: Dead guard — length === 0 never triggers

**False Positives (unmatched findings):**
- F-02 (behavioral/major): Zero-value sentinel teamId ?? 0 in auth checks
- F-03 (behavioral/major): Silent email error discard — err object unused
- F-06 (structural/minor): Zod schema recreated inside component per render
- F-07 (structural/minor): Untranslated tooltip "Remove email"
- F-08 (fragile/minor): Index-based React key in dynamic list
- F-10 (behavioral/minor): Organizer duplicate notification
- F-11 (structural/minor): Dead error fallback — template literal always truthy
- F-12 (behavioral/major): No booking status guard — guests added to cancelled/past bookings
- F-13 (behavioral/major): Fragile attendees[0].name in organizer email subject
- F-14 (behavioral/minor): 0 sentinel in organizer lookup
- F-16 (behavioral/minor): isInvalidEmail not cleared on input change
- F-17 (behavioral/minor): Broken label-input association (accessibility)
- F-18 (structural/minor): Server schema missing uniqueness validation
- F-19 (behavioral/minor): Case-sensitive email template dispatch

---

### cal_dot_com__calcom__cal.com__PR22532
**feat: add calendar cache status and actions (#22532)** — [https://github.com/calcom/cal.com/pull/22532](https://github.com/calcom/cal.com/pull/22532)
Golden: 2 | Findings: 10 | TP: 2 | FP: 8 | FN: 0 | P=20% R=100% F1=33%

**True Positives:**
- G1 (Medium) → F-03 (behavioral/major)
  Golden: The updateManyByCredentialId call uses an empty data object, which prevents Prisma's @updatedAt decorator from updating ...
  Finding: Empty data `{}` to updateMany may not touch SelectedCalendar.updatedAt
- G2 (Low) → F-04 (behavioral/major)
  Golden: logic: macOS-specific sed syntax with empty string after -i flag will fail on Linux systems
  Finding: Shell script uses macOS-only `sed -i ''` syntax, fails on Linux

**False Positives (unmatched findings):**
- F-01 (structural/minor): Migration comment contradicts actual SQL (comment-code drift)
- F-02 (behavioral/major): deleteCache handler throws plain Error instead of TRPCError (500 for auth failure)
- F-05 (fragile/major): Hardcoded "en-US" locale in Intl.DateTimeFormat ignoring user locale
- F-06 (structural/minor): deleteCache handler bypasses CalendarCacheRepository
- F-07 (behavioral/major): Cache deletion does not invalidate connectedCalendars query (stale UI)
- F-08 (behavioral/major): Second render site silently gains disableConnectionModification guard
- F-09 (behavioral/minor): Delete-cache confirm button has no loading/disabled guard
- F-10 (structural/minor): Empty actions container rendered when component returns null

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR1
**FEATURE: automatically downsize large images** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/1](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/1)
Golden: 3 | Findings: 11 | TP: 2 | FP: 9 | FN: 1 | P=18% R=67% F1=29%

**True Positives:**
- G1 (Medium) → F-01 (behavioral/critical)
  Golden: The downsize method is defined twice. The second definition, which expects a single dimensions string parameter, overrid...
  Finding: Duplicate `downsize` definition shadows 4-arg form — ArgumentError for existing callers
- G2 (Low) → F-02 (structural/major)
  Golden: Hardcoding maxSizeKB = 10 * 1024 ignores Discourse.SiteSettings['max_' + type + '_size_kb'], so the client-side limit ca...
  Finding: Client-side 10MB limit applies to all upload types, not just images

**False Negatives (missed golden):**
- G3 (Medium) [logic-error]: Passing 80% as the dimensions can fail for animated GIFs when allow_animated_thumbnails is true, since the animated path uses gifsicle --resize-fit wh...

**False Positives (unmatched findings):**
- F-03 (structural/major): 10MB hardcoded as three independent bare literals
- F-04 (behavioral/major): "80%" reduces pixel dimensions, not file size or quality
- F-05 (behavioral/minor): 413 handler shows hardcoded 10MB, not actual web server limit
- F-06 (behavioral/major): No post-loop guard — oversized file uploads proceed silently
- F-07 (structural/minor): Comment-code drift — comment overstates reduction guarantee
- F-08 (structural/minor): Asymmetric API — resize takes numeric args, downsize takes string
- F-09 (structural/minor): `optimize` signature changed without making it private
- F-10 (behavioral/minor): Zero-value sentinel silently disables auto-downsize
- F-11 (behavioral/major): In-place ImageMagick convert with identical source/dest path

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR2
**FEATURE: per-topic unsubscribe option in emails** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/2](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/2)
Golden: 2 | Findings: 13 | TP: 2 | FP: 11 | FN: 0 | P=15% R=100% F1=27%

**True Positives:**
- G1 (High) → F-01 (behavioral/critical)
  Golden: logic: Potential nil pointer exception - if no TopicUser record exists, tu will be nil and calling methods on it will cr...
  Finding: Nil dereference on TopicUser lookup
- G2 (Low) → F-07 (fragile/minor)
  Golden: Typo in property name: 'stopNotificiationsText' should be 'stopNotificationsText' (missing 'n' in 'Notifications')
  Finding: Misspelled property name fragile cross-file binding

**False Positives (unmatched findings):**
- F-02 (behavioral/major): GET route performs state mutation
- F-03 (behavioral/major): Missing unsubscribe_url interpolation breaks non-notification emails
- F-04 (fragile/minor): Route parameter naming mismatch `:topic_id` vs `:id`
- F-05 (behavioral/major): XSS via triple-brace rendering of user content
- F-06 (structural/minor): Non-transactional mutation before render
- F-08 (structural/minor): Nested KVO path on non-observable object
- F-09 (behavioral/major): Login requirement blocks one-click email unsubscribe
- F-10 (behavioral/major): Relative URL in email unsubscribe link
- F-11 (test-integrity/minor): No test for unsubscribe_url interpolation in email body
- F-12 (test-integrity/major): No controller spec for unsubscribe action
- F-13 (behavioral/minor): Unsubscribe bypasses TopicUser.change and MessageBus

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR3
**Add comprehensive email validation for blocked users** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/3](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/3)
Golden: 2 | Findings: 8 | TP: 2 | FP: 6 | FN: 0 | P=25% R=100% F1=40%

**True Positives:**
- G1 (Medium) → F-01 (structural/major)
  Golden: BlockedEmail.should_block_email? method has side effects during a read operation - it updates statistics even when just ...
  Finding: `should_block?` mixes query with stat-tracking write side effects
- G2 (Medium) → F-07 (behavioral/critical)
  Golden: Regex pattern @(#{domains}) only matches domain suffixes, not full domains. evil.example.com would match whitelist entry...
  Finding: Unanchored domain regex allows whitelist bypass via subdomain

**False Positives (unmatched findings):**
- F-02 (behavioral/major): Case-sensitive email matching allows trivial bypass of blocks
- F-03 (behavioral/minor): `record.save` return value unchecked — silent stat discard
- F-04 (test-integrity/major): EmailValidator spec missing whitelist/blacklist test coverage
- F-05 (test-integrity/minor): Test depends on ambient SiteSetting state (mock permissiveness)
- F-06 (behavioral/major): Race condition on stat counter (read-modify-write without lock)
- F-08 (behavioral/critical): Partial regex escaping — metacharacters cause crash or wrong matches

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR4
**Enhance embed URL handling and validation system** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/4](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/4)
Golden: 6 | Findings: 13 | TP: 3 | FP: 10 | FN: 3 | P=23% R=50% F1=32%

**True Positives:**
- G1 (Critical) → F-07 (behavioral/critical)
  Golden: SSRF vulnerability using open(url) without validation
  Finding: SSRF via Kernel#open in import_remote
- G2 (Medium) → F-02 (behavioral/major)
  Golden: The current origin validation using indexOf is insufficient and can be bypassed. An attacker could use a malicious domai...
  Finding: Origin check uses substring match instead of equality
- G5 (Medium) → F-06 (behavioral/critical)
  Golden: The TopicEmbed.import method is susceptible to a NoMethodError if the contents parameter is nil when attempting to appen...
  Finding: XSS via unescaped URL in HTML attribute

**False Negatives (missed golden):**
- G3 (Medium) [other]: postMessage targetOrigin should be the origin (scheme+host+port), not the full referrer URL; using the full URL will cause the message to be dropped a...
- G4 (Medium) [security]: The code sets X-Frame-Options: ALLOWALL which completely disables clickjacking protection. The referer validation can be bypassed (referer headers are...
- G6 (Medium) [race-condition]: The ERB block closes with end if, which is invalid Ruby/ERB and will raise at render; it should just be end to close the if block.

**False Positives (unmatched findings):**
- F-01 (behavioral/critical): Migration default sets all existing posts to raw_html
- F-08 (behavioral/critical): XSS via unescaped request.referer in inline JS
- F-13 (behavioral/critical): Stored XSS via unsanitized RSS feed content
- F-03 (behavioral/major): Nil crash on i.content in PollFeed
- F-04 (behavioral/major): Single-URL retrieval triggers full RSS feed import
- F-09 (behavioral/major): Content mutation via << includes I18n footer in SHA1
- F-11 (behavioral/major): No error handling for network failures
- F-12 (test-integrity/major): poll_feed method has zero test coverage
- F-05 (behavioral/minor): Bare port literals without scheme correlation
- F-10 (behavioral/minor): Protocol-relative URLs corrupted by absolutize_urls

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR5
**Optimize header layout performance with flexbox mixins** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/5](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/5)
Golden: 2 | Findings: 4 | TP: 2 | FP: 2 | FN: 0 | P=50% R=100% F1=67%

**True Positives:**
- G1 (Low) → F-02 (behavioral/major)
  Golden: Mixing float: left with flexbox causes layout issues. Further this PR removes the float-based right alignment for .d-hea...
  Finding: `order` on `.extra-info-wrapper` with no flex parent; retained float on `.badge-wrapper`
- G2 (Low) → F-01 (structural/major)
  Golden: -ms-align-items never existed in any version of IE/Edge; the correct legacy property is -ms-flex-align.
  Finding: Dead `-ms-align-items` vendor prefix in `align-items` mixin

**False Positives (unmatched findings):**
- F-03 (behavioral/minor): Padding unit change from `em` to `%` on `.small-action-desc`
- F-04 (structural/minor): Latent `-moz-box-ordinal-group` offset mismatch in `order` mixin

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR6
**UX: show complete URL path if website domain is same as instance domain** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/6](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/6)
Golden: 1 | Findings: 6 | TP: 1 | FP: 5 | FN: 0 | P=17% R=100% F1=29%

**True Positives:**
- G1 (Medium) → F-01 (fragile/major)
  Golden: The include_website_name method is missing the required ? suffix. Rails serializers expect include_ methods to end with ...
  Finding: `"." << website_host` mutates string literal; raises FrozenError with frozen_string_literal

**False Positives (unmatched findings):**
- F-02 (structural/minor): `URI(website.to_s)` parsed up to 4 times redundantly in one method call
- F-03 (test-integrity/major): elsif branch (same-depth subdomain matching) has zero test coverage
- F-04 (test-integrity/minor): No test for pathless URL or root-path-only URL in same-domain scenario
- F-05 (structural/minor): Bare `rescue nil` catches all StandardError subclasses, not just URI::InvalidURIError
- F-06 (behavioral/minor): Single-label host (bare TLD) passes `ends_with?` check, false-matching as parent domain

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR7
**scale-color $lightness must use $secondary for dark themes** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/7](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/7)
Golden: 3 | Findings: 6 | TP: 2 | FP: 4 | FN: 1 | P=33% R=67% F1=44%

**True Positives:**
- G2 (Low) → F-04 (behavioral/major)
  Golden: This change for desktop/user.css changes $primary from 30% to 50% for the light theme; most other changes preserve the o...
  Finding: desktop/user.scss .name: both args set to 50% instead of 30%/70%
- G3 (Low) → F-01 (behavioral/major)
  Golden: In topic-post.css the original code used $lightness: 70% but the replacement uses $lightness: 30% for the light theme. T...
  Finding: desktop/topic-post.scss: light/dark args swapped (30%↔70%)

**False Negatives (missed golden):**
- G1 (Low) [other]: In .topic-meta-data h5 a, the original code had color: scale-color($primary, $lightness: 30%) but was changed to dark-light-choose(scale-color($primar...

**False Positives (unmatched findings):**
- F-02 (behavioral/major): mobile/modal.scss: light/dark args swapped (70%↔30%)
- F-03 (behavioral/major): mobile/topic-post.scss h3: both args set to 50% instead of 20%/80%
- F-05 (behavioral/major): mobile/user.scss .name: both args set to 50% instead of 30%/70%
- F-06 (structural/major): Two distinct error modes in 5 of ~85 transformations

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR8
**FIX: proper handling of group memberships** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/8](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/8)
Golden: 3 | Findings: 13 | TP: 3 | FP: 10 | FN: 0 | P=23% R=100% F1=38%

**True Positives:**
- G1 (High) → F-07 (behavioral/minor)
  Golden:  The findMembers() call is now asynchronous and unhandled. The controller may not have member data immediately available...
  Finding: No rejection handler on fire-and-forget `findMembers()` calls
- G2 (Medium) → F-04 (behavioral/minor)
  Golden: In the next action, capping the next offset at user_count can produce an empty page (e.g., total equal to limit results ...
  Finding: `totalPages` off-by-one when user_count is exact multiple of limit
- G3 (Medium) → F-09 (test-integrity/minor)
  Golden: HTTP method mismatch in .remove_member - test uses PUT but remove_member action expects DELETE
  Finding: Test uses wrong HTTP method (PUT instead of DELETE) for remove_member

**False Positives (unmatched findings):**
- F-01 (structural/info): `findMembers()` returns undefined instead of promise on early exit
- F-02 (behavioral/major): `remove_member` silent no-op for non-members, misleading success response
- F-03 (behavioral/major): `add_members` silently skips invalid usernames, returns success
- F-05 (behavioral/minor): `showingLast` guard fails at true last page (downstream of F-04)
- F-06 (structural/minor): Bare literal 50 for page size in JS model and Ruby controller
- F-08 (behavioral/minor): TODO comment documents unimplemented input clearing after add
- F-10 (behavioral/minor): `create` action ignores `alias_level` from params
- F-11 (behavioral/minor): No upper bound on client-supplied `limit` parameter
- F-12 (fragile/minor): Tests hardcode `id: 1` for automatic group instead of fabricating
- F-13 (behavioral/minor): `{{#unless automatic}}` unresolvable in item view — remove button always renders

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR9
**FEATURE: Localization fallbacks (server-side)** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/9](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/9)
Golden: 2 | Findings: 2 | TP: 0 | FP: 2 | FN: 2 | P=0% R=0% F1=0%

**False Negatives (missed golden):**
- G1 (Low) [race-condition]: Thread-safety issue with lazy @loaded_locales
- G2 (Low) [data-integrity]: Consider normalizing the input locale (e.g., to a symbol) when checking/loading here to avoid double-loading if the same locale is passed as a String ...

**False Positives (unmatched findings):**
- F-01 (fragile/minor): Implicit ordering contract: `ensure_loaded!` reads `I18n.locale` but diff does not confirm assignment precedes call
- F-02 (behavioral/minor): Fallback scope expanded from production-only to all environments including test

---

### discourse__ai-code-review-evaluation__discourse-graphite__PR10
**FEATURE: Can edit category/host relationships for embedding** — [https://github.com/ai-code-review-evaluation/discourse-graphite/pull/10](https://github.com/ai-code-review-evaluation/discourse-graphite/pull/10)
Golden: 4 | Findings: 16 | TP: 2 | FP: 14 | FN: 2 | P=12% R=50% F1=20%

**True Positives:**
- G1 (Critical) → F-10 (behavioral/major)
  Golden: NoMethodError before_validation in EmbeddableHost
  Finding: before_validation nil crash on host
- G2 (Medium) → F-02 (behavioral/major)
  Golden: The update and destroy methods in Admin::EmbeddableHostsController do not validate the existence of the EmbeddableHost r...
  Finding: Nil dereference in update/destroy for missing records

**False Negatives (missed golden):**
- G3 (Medium) [data-integrity]: record_for_host compares lower(host) = ? but does not normalize the parameter’s case, so mixed‑case referer hosts may fail to match even though compar...
- G4 (High) [data-integrity]: Because this migration inserts embeddable_hosts rows with raw SQL, any existing embeddable_hosts values that include http:// or /https:// or path segm...

**False Positives (unmatched findings):**
- F-01 (structural/critical): SQL injection in migration via string interpolation
- F-03 (structural/minor): EmbeddingController#update silently ignores all payload
- F-04 (behavioral/minor): Non-global underscore replace in basePath
- F-05 (structural/major): Fabricator files have swapped content
- F-06 (test-integrity/major): Controller specs test only inheritance, no actions
- F-07 (test-integrity/minor): "is false if embeddable_host is blank" passes vacuously
- F-08 (test-integrity/minor): Missing explicit setup for "no host" test condition
- F-09 (structural/minor): []` fallback and null entries in plural hydration
- F-11 (behavioral/major): Missing categories sideload in EmbeddingSerializer
- F-12 (behavioral/major): Missing .catch on destroyRecord in delete action
- F-13 (behavioral/major): Missing strong parameters guard in save_host
- F-14 (behavioral/major): Unguarded nil dereference on PG result in migration
- F-15 (behavioral/major): Host validation regex rejects valid TLDs > 5 chars
- F-16 (fragile/minor): Missing array guard before .map() in plural hydration

---

### grafana__grafana__grafana__PR79265
**Anonymous: Add configurable device limit** — [https://github.com/grafana/grafana/pull/79265](https://github.com/grafana/grafana/pull/79265)
Golden: 5 | Findings: 12 | TP: 3 | FP: 9 | FN: 2 | P=25% R=60% F1=35%

**True Positives:**
- G1 (High) → F-03 (behavioral/major)
  Golden: Race condition: Multiple concurrent requests could pass the device count check simultaneously and create devices beyond ...
  Finding: TOCTOU race: count-then-insert device limit check is not atomic
- G2 (Medium) → F-05 (behavioral/major)
  Golden: Anonymous authentication now fails entirely if anonDeviceService.TagDevice returns ErrDeviceLimitReached. Previously, de...
  Finding: `ErrDeviceLimitReached` blocks anonymous auth entirely — fire-and-forget converted to sync auth gate
- G5 (Low) → F-04 (behavioral/major)
  Golden: Time window calculation inconsistency: Using device.UpdatedAt.UTC().Add(-anonymousDeviceExpiration) as the lower bound b...
  Finding: `updateDevice` WHERE clause anchors time window on `device.UpdatedAt` instead of `time.Now()`

**False Negatives (missed golden):**
- G3 (Medium) [type-error]: This call won’t compile: dbSession.Exec(args...) is given a []interface{} where the first element is the query, but Exec’s signature requires a first ...
- G4 (Low) [logic-error]: Returning ErrDeviceLimitReached when no rows were updated is misleading; the device might not exist.

**False Positives (unmatched findings):**
- F-01 (behavioral/major): Zero-value sentinel ambiguity: Go int64 always sends `0`, TS type expects `undefined` for "no limit"
- F-02 (structural/minor): Duplicate `anonymousDeviceExpiration` constant in `database.go` and `api.go`
- F-06 (behavioral/major): Debug-level log before hard auth failure — log severity doesn't match operational impact
- F-07 (behavioral/major): Panic recovery removed when goroutine was replaced with synchronous call
- F-08 (structural/major): Interface-to-concrete coupling: constructor no longer accepts `AnonStore` interface
- F-09 (fragile/minor): Request context passed with no timeout — removed 2-minute timeout constant
- F-10 (behavioral/minor): `TagDevice` now propagates all `tagDeviceUI` errors, not just `ErrDeviceLimitReached`
- F-11 (test-integrity/minor): Test covers rejection path only; update success path for existing device at limit is untested
- F-12 (fragile/major): Closure captures and mutates outer `args` variable — corrupts argument list on retry

---

### grafana__grafana__grafana__PR103633
**AuthZService: improve authz caching** — [https://github.com/grafana/grafana/pull/103633](https://github.com/grafana/grafana/pull/103633)
Golden: 2 | Findings: 5 | TP: 1 | FP: 4 | FN: 1 | P=20% R=50% F1=29%

**True Positives:**
- G2 (Low) → F-01 (test-integrity/major)
  Golden: The test comment says the cached permissions 'allow access', but the map stores false for dashboards:uid:dash1, so check...
  Finding: "Should deny on explicit cache deny entry" uses `false` in permCache — non-enforcing fixture

**False Negatives (missed golden):**
- G1 (High) [data-integrity]: The Check operation exhibits asymmetric cache trust logic: cached permission grants are trusted and returned immediately, but cached denials from the ...

**False Positives (unmatched findings):**
- F-02 (behavioral/minor): Denial cache key collision via underscore delimiter in name/parent fields
- F-03 (behavioral/minor): Missing `permissionCacheUsage` metric on checkPermission error path
- F-04 (fragile/minor): Denial cache key uses raw UserUID, permission cache uses resolved UID
- F-05 (test-integrity/minor): "Outdated cache" test exercises same code path as cache miss test

---

### grafana__grafana__grafana__PR76186
**Plugins: Chore: Renamed instrumentation middleware to metrics middleware** — [https://github.com/grafana/grafana/pull/76186](https://github.com/grafana/grafana/pull/76186)
Golden: 2 | Findings: 7 | TP: 1 | FP: 6 | FN: 1 | P=14% R=50% F1=22%

**True Positives:**
- G2 (Low) → F-01 (behavioral/major)
  Golden: The traceID is no longer logged for plugin requests. During a refactoring, the tracing import and the logic to extract a...
  Finding: traceID field silently removed from log output

**False Negatives (missed golden):**
- G1 (High) [null-safety]: The ContextualLoggerMiddleware methods (QueryData, CallResource, CheckHealth, CollectMetrics) panic when a nil request is received. This occurs becaus...

**False Positives (unmatched findings):**
- F-02 (test-integrity/major): TestLogger.FromContext returns zero-state logger, ignoring context
- F-03 (fragile/major): grafanaInfraLogWrapper.FromContext silent type assertion fallback
- F-04 (behavioral/major): pluginId/endpoint depend on implicit middleware ordering
- F-05 (structural/minor): Stream methods pass through without context enrichment (pre-existing)
- F-06 (test-integrity/minor): Test function name not updated after type rename
- F-07 (test-integrity/major): No test coverage for new ContextualLoggerMiddleware

---

### grafana__grafana__grafana__PR107534
**Advanced Query Processing Architecture** — [https://github.com/grafana/grafana/pull/107534](https://github.com/grafana/grafana/pull/107534)
Golden: 1 | Findings: 8 | TP: 0 | FP: 8 | FN: 1 | P=0% R=0% F1=0%

**False Negatives (missed golden):**
- G1 (Low) [test-quality]: The applyTemplateVariables method is called with request.filters as the third parameter, but this parameter is not used in the corresponding test setu...

**False Positives (unmatched findings):**
- F-01 (test-integrity/major): querySplitting test asserts only first `runQuery` call
- F-02 (test-integrity/major): shardQuerySplitting test asserts only first `runQuery` call
- F-03 (fragile/minor): Bare literal `5` in call count assertion
- F-04 (test-integrity/major): `step` field interpolation path not demonstrated
- F-05 (structural/minor): Filter ordering inconsistency across parallel paths
- F-06 (test-integrity/minor): Mutating mock masks map vs original reference
- F-07 (test-integrity/minor): Missing guard before `calls[0]` dereference
- F-08 (behavioral/minor): Empty-expr filter runs pre-interpolation

---

### grafana__grafana__grafana__PR106778
**Notification Rule Processing Engine** — [https://github.com/grafana/grafana/pull/106778](https://github.com/grafana/grafana/pull/106778)
Golden: 2 | Findings: 13 | TP: 0 | FP: 13 | FN: 2 | P=0% R=0% F1=0%

**False Negatives (missed golden):**
- G1 (Medium) [api-misuse]: The rendered GrafanaRuleListItem is missing the required key prop for React list items. This can cause rendering issues when the list order changes.
- G2 (High) [api-misuse]: RuleActionsButtons is invoked with only promRule, but SilenceGrafanaRuleDrawer inside RuleActionsButtons still depends on a Grafana Ruler rule being p...

**False Positives (unmatched findings):**
- F-01 (fragile/major): Unstable memo dependency — inline array literals defeat useMemo in ability hooks
- F-02 (structural/minor): Leftover `// duplicate` comment in useAllGrafanaPromRuleAbilities
- F-03 (structural/major): isFederated hardcoded to false — dead conditional guard removes federated rule immutability
- F-04 (structural/minor): Redundant type narrowing inside alertingRule guard
- F-05 (behavioral/minor): returnTo query param dropped from GrafanaRuleListItem href
- F-06 (test-integrity/info): Count-only assertion without Delete absence check
- F-07 (behavioral/major): Semantic drift in deprecated useAllAlertRuleAbilities delegation path
- F-08 (structural/info): Dead operation prop/import in GrafanaRuleListItem
- F-09 (behavioral/major): isAlertingRule in wrong ability tuple dimension for Silence
- F-10 (test-integrity/major): Test grants AlertingRuleDelete but doesn't assert Delete presence/absence
- F-11 (behavioral/major): Silent removal of Creating/Deleting transitional states and logWarning
- F-12 (behavioral/minor): OR semantics when both ruler and prom present — inconsistent ability combination
- F-13 (fragile/minor): Inconsistent null-guarding in useAllGrafanaPromRuleAbilities

---

### grafana__grafana__grafana__PR90045
**Dual Storage Architecture** — [https://github.com/grafana/grafana/pull/90045](https://github.com/grafana/grafana/pull/90045)
Golden: 3 | Findings: 11 | TP: 3 | FP: 8 | FN: 0 | P=27% R=100% F1=43%

**True Positives:**
- G1 (Medium) → F-05 (behavioral/minor)
  Golden: The context is being created with d.Log instead of the log variable that was initialized with additional context values ...
  Finding: Delete context uses base logger `d.Log` instead of enriched `log`
- G2 (High) → F-01 (behavioral/major)
  Golden: Bug: calling recordLegacyDuration when storage operation fails should be recordStorageDuration.
  Finding: Create error path calls `recordLegacyDuration` instead of `recordStorageDuration`
- G3 (Medium) → F-04 (behavioral/minor)
  Golden: Inconsistency: using name instead of options.Kind for metrics recording differs from other methods.
  Finding: Delete success path passes `name` instead of `options.Kind` to metrics

**False Positives (unmatched findings):**
- F-02 (behavioral/major): Update error path calls `recordLegacyDuration` instead of `recordStorageDuration`
- F-03 (behavioral/major): DeleteCollection goroutine calls `recordStorageDuration` instead of `recordLegacyDuration`
- F-06 (test-integrity/major): Delete/DeleteCollection tests have no Legacy mock expectations
- F-07 (test-integrity/minor): Create/Update tests lack goroutine sync and AssertExpectations
- F-08 (fragile/minor): Mode1_test removes local prometheus registry, uses shared `p`
- F-09 (behavioral/critical): All goroutines capture request context; Legacy writes cancelled when handler returns
- F-10 (test-integrity/minor): TestMode3_Get creates local registry; other Mode3 tests use shared `p`
- F-11 (test-integrity/minor): Create error test registers mock via Legacy setup, passes only due to shared mock

---

### grafana__grafana__grafana__PR80329
**Database Performance Optimizations** — [https://github.com/grafana/grafana/pull/80329](https://github.com/grafana/grafana/pull/80329)
Golden: 1 | Findings: 9 | TP: 1 | FP: 8 | FN: 0 | P=11% R=100% F1=20%

**True Positives:**
- G1 (Low) → F-01 (behavioral/major)
  Golden: The code uses Error log level for what appears to be debugging information. This will pollute error logs in production. ...
  Finding: `r.log.Error` used for routine cleanup diagnostics on every batch

**False Positives (unmatched findings):**
- F-02 (behavioral/minor): SQLite inline-ID guard checks config batch size, not actual `len(ids)`
- F-03 (fragile/minor): `untilDoneOrCancelled` loop exit conflates "no IDs fetched" with "no rows deleted"
- F-04 (behavioral/major): Log calls serialize full `[]int64` ID slices (up to 32K elements)
- F-05 (behavioral/major): Cleanup ticker reduced from 10min to 1min without documentation
- F-06 (test-integrity/minor): SQLite-specific test not skipped on non-SQLite backends
- F-07 (structural/minor): `fetchIDs` parameter "condition" receives full SQL clause fragment
- F-08 (test-integrity/minor): Test name references SQLite >= 3.32.0 limit but code guards at pre-3.32.0 (999)
- F-09 (test-integrity/minor): `WithDbSession` callbacks return nil unconditionally; outer error check is dead

---

### grafana__grafana__grafana__PR90939
**Frontend Asset Optimization** — [https://github.com/grafana/grafana/pull/90939](https://github.com/grafana/grafana/pull/90939)
Golden: 2 | Findings: 2 | TP: 1 | FP: 1 | FN: 1 | P=50% R=50% F1=50%

**True Positives:**
- G1 (Medium) → F-01 (behavioral/major)
  Golden: The GetWebAssets function implements an incomplete double-checked locking pattern for caching web assets. The function f...
  Finding: Missing double-check under write lock — TOCTOU race causes redundant disk loads on cold cache

**False Negatives (missed golden):**
- G2 (High) [race-condition]: In addition to the missing double-check, the function has a critical flaw in its error handling: it unconditionally assigns the fetch result to the ca...

**False Positives (unmatched findings):**
- F-02 (structural/info): Ambient state access — package-level globals for cache and mutex

---

### grafana__grafana__grafana__PR94942
**Advanced SQL Analytics Framework** — [https://github.com/grafana/grafana/pull/94942](https://github.com/grafana/grafana/pull/94942)
Golden: 2 | Findings: 3 | TP: 2 | FP: 1 | FN: 0 | P=67% R=100% F1=80%

**True Positives:**
- G1 (Critical) → F-01 (behavioral/critical)
  Golden: The enableSqlExpressions function has flawed logic that always returns false, effectively disabling SQL expressions unco...
  Finding: `enableSqlExpressions` always returns `false` — SQL expressions permanently blocked
- G2 (High) → F-02 (structural/major)
  Golden: Several methods such as NewInMemoryDB().RunCommands and db.QueryFramesInto return 'not implemented'.
  Finding: Stub DB is dead infrastructure due to F-01's broken gate

**False Positives (unmatched findings):**
- F-03 (fragile/minor): Bare string error is semantically misleading and not inspectable

---

### grafana__grafana__grafana__PR97529
**Unified Storage Performance Optimizations** — [https://github.com/grafana/grafana/pull/97529](https://github.com/grafana/grafana/pull/97529)
Golden: 2 | Findings: 7 | TP: 1 | FP: 6 | FN: 1 | P=14% R=50% F1=22%

**True Positives:**
- G1 (High) → F-03 (behavioral/major)
  Golden: A race condition in BuildIndex allows multiple goroutines to concurrently build the same expensive index for the same ke...
  Finding: Concurrent build race for same-key file-backed indexes

**False Negatives (missed golden):**
- G2 (High) [race-condition]: Calling s.search.TotalDocs() here may race with concurrent index creation: TotalDocs iterates b.cache without synchronization, and the event watcher g...

**False Positives (unmatched findings):**
- F-01 (behavioral/minor): Duplicate error log on Init failure
- F-02 (fragile/minor): Non-deferred mutex unlock in BuildIndex
- F-04 (test-integrity/minor): Unconditionally skipped postgres test with no tracker reference
- F-05 (behavioral/info): Context discard fixes — pre-existing bugs corrected
- F-06 (behavioral/major): History()/Origin() nil-safety gap after Init guard removal
- F-07 (fragile/minor): Context discard in bleve.go BuildIndex missed by PR's fix sweep

---

### keycloak__ai-code-review-evaluation__keycloak-greptile__PR1
**Fixing Re-authentication with passkeys** — [https://github.com/ai-code-review-evaluation/keycloak-greptile/pull/1](https://github.com/ai-code-review-evaluation/keycloak-greptile/pull/1)
Golden: 2 | Findings: 8 | TP: 2 | FP: 6 | FN: 0 | P=25% R=100% F1=40%

**True Positives:**
- G1 (Medium) → F-01 (structural/minor)
  Golden: ConditionalPasskeysEnabled() called without UserModel parameter
  Finding: Zero-arg `isConditionalPasskeysEnabled()` in UsernameForm has no visible definition in the diff
- G2 (Medium) → F-02 (structural/minor)
  Golden: With isConditionalPasskeysEnabled(UserModel user) requiring user != null, authenticate(...) will not call webauthnAuth.f...
  Finding: `isConditionalPasskeysEnabled` name implies capability check but encodes user-presence gate

**False Positives (unmatched findings):**
- F-03 (test-integrity/minor): Dead `fail()` code in negative element assertions; inconsistent with codebase `assertThrows` pattern
- F-04 (fragile/info): Null safety in `fillContextForm` moved from structural guard to implicit method contract
- F-05 (test-integrity/minor): `reauthenticationOfUserWithoutPasskey` test name says "user without passkey" but only tests realm policy
- F-06 (fragile/minor): Bare string literal "Please re-authenticate to continue" repeated in 3 test assertions
- F-07 (test-integrity/minor): `events.clear()` removed from `webauthnLoginWithExternalKey_reauthenticationWithPasswordOrPasskey`
- F-08 (test-integrity/minor): Missing CREDENTIAL_TYPE assertion in `reauthenticationOfUserWithoutPasskey` password-login event

---

### keycloak__keycloak__keycloak__PR32918
**Add caching support for IdentityProviderStorageProvider.getForLogin operations** — [https://github.com/keycloak/keycloak/pull/32918](https://github.com/keycloak/keycloak/pull/32918)
Golden: 2 | Findings: 7 | TP: 1 | FP: 6 | FN: 1 | P=14% R=50% F1=22%

**True Positives:**
- G2 (Medium) → F-03 (test-integrity/major)
  Golden: Cleanup reference uses incorrect alias - should be 'idp-alias-' + i instead of 'alias'.
  Finding: Cleanup loop uses literal `"alias"` instead of actual IDP alias; 21 IDPs leak

**False Negatives (missed golden):**
- G1 (Critical) [logic-error]: Recursive caching call using session instead of delegate

**False Positives (unmatched findings):**
- F-01 (behavioral/critical): Cache-warm path omits `createOrganizationAwareIdentityProviderModel`; delegate paths apply it
- F-02 (behavioral/major): `isEnabled()` re-check is a call-site patch for F-01's wrapping asymmetry
- F-04 (behavioral/minor): Cache path returns unordered `HashSet` stream; delegate path preserves storage order
- F-05 (fragile/minor): Two `addRevisioned` calls use different revision sources
- F-06 (test-integrity/major): No test exercises BROKER_PUBLIC exclusion for org-linked IDPs
- F-07 (test-integrity/major): IDP 20 cleanup uses literal `"alias"` instead of `"idp-alias-20"`

---

### keycloak__keycloak__keycloak__PR33832
**Add AuthzClientCryptoProvider for authorization client cryptographic operations** — [https://github.com/keycloak/keycloak/pull/33832](https://github.com/keycloak/keycloak/pull/33832)
Golden: 2 | Findings: 8 | TP: 1 | FP: 7 | FN: 1 | P=12% R=50% F1=20%

**True Positives:**
- G2 (Low) → F-01 (structural/minor)
  Golden: Dead code exists where ASN1Encoder instances are created and written to, but their results are immediately discarded. Th...
  Finding: Dead encoder calls — two ASN1Encoder instances created and discarded

**False Negatives (missed golden):**
- G1 (High) [api-misuse]: Returns wrong provider (default keystore instead of BouncyCastle)

**False Positives (unmatched findings):**
- F-02 (test-integrity/major): Wrong EC curve for ES384/ES512 tests — P-256 key used for all algorithms
- F-03 (fragile/major): CryptoIntegration.init() added to only one of multiple factory methods
- F-04 (fragile/minor): Logger.debugf() passed dynamic string as format argument
- F-05 (structural/minor): Bare integer literals (100, 200) for provider ordering with no shared constant
- F-06 (behavioral/minor): readSequence() silently returns empty list on indefinite-length DER encoding
- F-07 (structural/minor): readSequence() length tracking has no underflow guard for malformed input
- F-08 (test-integrity/major): Test verifies codec self-consistency but not JCA Signature.verify() interop

---

### keycloak__keycloak__keycloak__PR36882
**Add rolling-updates feature flag and compatibility framework** — [https://github.com/keycloak/keycloak/pull/36882](https://github.com/keycloak/keycloak/pull/36882)
Golden: 1 | Findings: 9 | TP: 0 | FP: 9 | FN: 1 | P=0% R=0% F1=0%

**False Negatives (missed golden):**
- G1 (Medium) [api-misuse]: Incorrect method call for exit codes. The picocli.exit() method calls System.exit() directly, which is problematic:

**False Positives (unmatched findings):**
- F-01 (structural/minor): Bare string literal `"rolling-updates"` in `printFeatureDisabled()` instead of `Profile.Feature.ROLLING_UPDATES.getKey()`
- F-02 (test-integrity/major): `testFeatureNotEnabled` only covers `metadata` subcommand, not `check`; no exit code assertion for `FEATURE_DISABLED=4`
- F-03 (test-integrity/minor): `testMissingOptionOnSave` uses negative-only assertion with no positive verification (pre-existing)
- F-04 (fragile/minor): `kc.adoc` template macro unconditionally hardcodes `--features=rolling-updates`
- F-05 (fragile/minor): `Dockerfile-custom-image` hardcodes `--features=rolling-updates` in build step
- F-06 (structural/minor): Identical feature-gate guard block duplicated in `UpdateCompatibilityCheck.run()` and `UpdateCompatibilityMetadata.run()`
- F-07 (test-integrity/major): `testWrongVersions` missing exit code assertion after `RECREATE_UPGRADE_EXIT_CODE` changed from 4 to 3
- F-08 (structural/minor): `RECREATE_UPGRADE_EXIT_CODE` value changed from 4 to 3 on public interface with no changelog or migration note
- F-09 (fragile/minor): `ENABLE_FEATURE` test constant uses bare string `"--features=rolling-updates"` instead of composing from typed enum

---

### keycloak__keycloak__keycloak__PR36880
**Add Client resource type and scopes to authorization schema** — [https://github.com/keycloak/keycloak/pull/36880](https://github.com/keycloak/keycloak/pull/36880)
Golden: 3 | Findings: 8 | TP: 1 | FP: 7 | FN: 2 | P=12% R=33% F1=18%

**True Positives:**
- G1 (High) → F-02 (behavioral/major)
  Golden: Inconsistent feature flag bug causing orphaned permissions. The AdminPermissions event listener, responsible for cleanin...
  Finding: behavioral | major | Feature-flag scope creep

**False Negatives (missed golden):**
- G2 (High) [other]: In hasPermission(ClientModel client, String scope), the resource lookup uses findByName(server, client.getId(), server.getId()), but AdminPermissionsS...
- G3 (High) [null-safety]: In getClientsWithPermission(String scope), iterating resourceStore.findByType(server, AdminPermissionsSchema.CLIENTS_RESOURCE_TYPE) and returning reso...

**False Positives (unmatched findings):**
- F-01 (structural/minor): structural | minor | Dead infrastructure
- F-03 (behavioral/critical): behavioral | critical | Runtime crash on client deletion in V2
- F-04 (structural/minor): structural | minor | Static/instance inconsistency in test helpers
- F-05 (test-integrity/minor): test-integrity | minor | Test isolation gap in map-roles test
- F-07 (structural/minor): structural | minor | Javadoc comment-code drift on void methods
- F-08 (behavioral/major): behavioral | major | Manage-view transitivity gap at all-clients level
- F-09 (test-integrity/minor): test-integrity | minor | Test state leak — roles not cleaned up

---

### keycloak__keycloak__keycloak__PR37038
**Add Groups resource type and scopes to authorization schema** — [https://github.com/keycloak/keycloak/pull/37038](https://github.com/keycloak/keycloak/pull/37038)
Golden: 2 | Findings: 6 | TP: 1 | FP: 5 | FN: 1 | P=17% R=50% F1=25%

**True Positives:**
- G2 (High) → F-01 (behavioral/critical)
  Golden: In getGroupIdsWithViewPermission, hasPermission is called with groupResource.getId() and the same groupResource.getId() ...
  Finding: `getGroupIdsWithViewPermission()` uses Resource internal ID instead of group UUID

**False Negatives (missed golden):**
- G1 (High) [logic-error]: Incorrect permission check in canManage() method

**False Positives (unmatched findings):**
- F-02 (structural/minor): Javadoc copy-paste error on `requireManageMembers`
- F-03 (test-integrity/minor): Double-close of Response in test setup
- F-04 (test-integrity/major): No test isolates the ID-type contract of `getGroupIdsWithViewPermission()`
- F-05 (behavioral/major): `AdminRoles.ADMIN` removed from V2 per-user permission checks
- F-07 (test-integrity/minor): No test for ADMIN role behavior in V2 mode

---

### keycloak__keycloak__keycloak__PR37429
**Add HTML sanitizer for translated message resources** — [https://github.com/keycloak/keycloak/pull/37429](https://github.com/keycloak/keycloak/pull/37429)
Golden: 4 | Findings: 13 | TP: 3 | FP: 10 | FN: 1 | P=23% R=75% F1=35%

**True Positives:**
- G1 (Medium) → F-06 (behavioral/critical)
  Golden: The translation is in Italian instead of Lithuanian. This should be translated to Lithuanian to match the file's locale ...
  Finding: Lithuanian `totpStep1` replaced with Italian text
- G2 (Medium) → F-07 (behavioral/major)
  Golden: The totpStep1 value uses Traditional Chinese terms in the Simplified Chinese file (zh_CN), which is likely incorrect for...
  Finding: `zh_CN` `totpStep1` replaced with Traditional Chinese
- G3 (Low) → F-01 (behavioral/major)
  Golden: The anchor sanitization logic has a potential issue where it consumes English matcher groups without proper validation. ...
  Finding: `santizeAnchors` matcher/string desync on multi-anchor strings

**False Negatives (missed golden):**
- G4 (Low) [security]: The method name 'santizeAnchors' should be 'sanitizeAnchors' (missing 'i').

**False Positives (unmatched findings):**
- F-02 (behavioral/major): `replaceFirst` removes wrong occurrence for repeated anchors
- F-03 (fragile/major): Full-path `replaceAll` can corrupt directory components
- F-04 (behavioral/major): OWASP sanitizer `<br>` normalization causes false positives
- F-05 (behavioral/minor): `containsHtml()` regex misses closing HTML tags
- F-08 (structural/minor): Policy fields should be `static final` constants
- F-09 (behavioral/major): `RuntimeException` escapes `verify()` IOException catch
- F-10 (behavioral/major): Substring index overlap throws `StringIndexOutOfBoundsException`
- F-11 (test-integrity/minor): `illegalHtmlTag_en` test exercises self-comparison path
- F-12 (behavioral/minor): `<!-- -->` sentinel stripping can mask violations
- F-13 (test-integrity/minor): `normalizeValue()` branches have no test coverage

---

### keycloak__keycloak__keycloak__PR37634
**Implement access token context encoding framework** — [https://github.com/keycloak/keycloak/pull/37634](https://github.com/keycloak/keycloak/pull/37634)
Golden: 4 | Findings: 4 | TP: 3 | FP: 1 | FN: 1 | P=75% R=75% F1=75%

**True Positives:**
- G1 (Critical) → F-01 (behavioral/critical)
  Golden: Wrong parameter in null check (grantType vs. rawTokenId)
  Finding: AccessTokenContext constructor null-checks `grantType` twice, never checks `rawTokenId`
- G2 (High) → F-02 (test-integrity/critical)
  Golden: In isAccessTokenId, the substring for the grant shortcut and the equality check look inverted: the grant shortcut occupi...
  Finding: isAccessTokenId matcher inverted boolean — passes wrong tokens, fails correct ones
- G4 (Low) → F-04 (test-integrity/minor)
  Golden:  Catching generic RuntimeException is too broad. The implementation throws IllegalArgumentException specifically - catch...
  Finding: testIncorrectGrantType catches RuntimeException broadly, masks wrong exception types

**False Negatives (missed golden):**
- G3 (Low) [style]: Javadoc mentions "usually like 3-letters shortcut" but some implementations use 2-letter shortcuts ("ac", "cc", "rt", "te", "pc", "ci", "ro"). Conside...

**False Positives (unmatched findings):**
- F-03 (test-integrity/critical): isAccessTokenId matcher substring(3,5) extracts wrong positions — should be (4,6)

---

### keycloak__keycloak__keycloak__PR38446
**Implement recovery key support for user storage providers** — [https://github.com/keycloak/keycloak/pull/38446](https://github.com/keycloak/keycloak/pull/38446)
Golden: 2 | Findings: 8 | TP: 2 | FP: 6 | FN: 0 | P=25% R=100% F1=40%

**True Positives:**
- G1 (Medium) → F-03 (behavioral/major)
  Golden: Unsafe raw List deserialization without type safety. Calling Optional.get() directly on the Optional returned by Recover...
  Finding: Unconditional `Optional.get()` in `RecoveryAuthnCodeInputLoginBean` — crashes on absent credential
- G2 (Low) → F-02 (structural/minor)
  Golden: After creating the RecoveryAuthnCodesCredentialModel, consider setting its id from the stored credential (e.g., myUser.r...
  Finding: Empty string `""` credential ID in `UserCredentialModel` constructor

**False Positives (unmatched findings):**
- F-01 (structural/major): Bare string literal `"keycloak-recovery-authn-codes"` instead of `PROVIDER_ID` constant
- F-04 (structural/minor): Raw `List` type (no generics) in `isValid()` recovery code deserialization
- F-05 (fragile/minor): Test assertion hardcoded to recovery code index 0
- F-06 (structural/major): Silent `IOException` discard in `getCredentials()` — credential silently disappears
- F-07 (test-integrity/minor): Test only exercises recovery code index 0, no coverage of other positions
- F-08 (structural/minor): Dead delay infrastructure with typo `"delayed-suthenticator-config"`

---

### keycloak__keycloak__keycloak__PR40940
**Fix concurrent group access to prevent NullPointerException** — [https://github.com/keycloak/keycloak/pull/40940](https://github.com/keycloak/keycloak/pull/40940)
Golden: 2 | Findings: 3 | TP: 2 | FP: 1 | FN: 0 | P=67% R=100% F1=80%

**True Positives:**
- G1 (Critical) → F-01 (behavioral/critical)
  Golden: Returning null from getSubGroupsCount() violates the GroupModel contract (Javadoc says it never returns null) and may le...
  Finding: Null return from `getSubGroupsCount()` violates `GroupModel` contract, relocates NPE to callers
- G2 (Medium) → F-02 (test-integrity/major)
  Golden: The reader thread isn’t waited for; flipping deletedAll to true and asserting immediately can race and miss exceptions a...
  Finding: Reader thread not joined before assertion — race can miss exceptions

**False Positives (unmatched findings):**
- F-03 (test-integrity/major): Discarded thread reference leaks on failure path — thread spins indefinitely

---

### sentry__ai-code-review-evaluation__sentry-greptile__PR1
**Enhanced Pagination Performance for High-Volume Audit Logs** — [https://github.com/ai-code-review-evaluation/sentry-greptile/pull/1](https://github.com/ai-code-review-evaluation/sentry-greptile/pull/1)
Golden: 3 | Findings: 10 | TP: 3 | FP: 7 | FN: 0 | P=30% R=100% F1=46%

**True Positives:**
- G1 (High) → F-01 (behavioral/critical)
  Golden: Django querysets do not support negative slicing
  Finding: `OptimizedCursorPaginator` negative-offset branch crashes with Django `AssertionError`
- G2 (High) → F-03 (behavioral/critical)
  Golden: When requests are authenticated with API keys or org auth tokens (which have user_id=None), organization_context.member ...
  Finding: `organization_context.member` `None` → `AttributeError` crashes ALL API-key requests unconditionally
- G3 (High) → F-04 (behavioral/critical)
  Golden: get_item_key assumes a numeric key, but the paginator is used with order_by=-datetime in the audit logs endpoint; callin...
  Finding: `get_item_key()` calls `math.floor` on `datetime` → `TypeError` on every optimized paginator result

**False Positives (unmatched findings):**
- F-02 (behavioral/critical): `DateTimePaginator` `is_prev` branch allows negative offset → Django `AssertionError`
- F-05 (structural/minor): Docstring claims "Streamlined boundary condition handling" and "Optimized query path" — neither implemented
- F-06 (structural/minor): False safety comment: "permissions checked at queryset level" is irrelevant to negative slice indexing
- F-07 (structural/minor): `max(0, offset) if not cursor.is_prev else offset` duplicated across both paginators
- F-08 (structural/major): `enable_advanced_features=True` kwarg may be silently dropped by `paginate()` — dead feature activation
- F-09 (structural/major): `Cursor.__init__` stores `int(offset)` with no lower-bound validation — root cause of F-01/F-02
- F-10 (structural/major): `OptimizedCursorPaginator.get_result()` fully reimplements `BasePaginator.get_result()` scaffolding

---

### sentry__ai-code-review-evaluation__sentry-greptile__PR2
**Optimize spans buffer insertion with eviction during insert** — [https://github.com/ai-code-review-evaluation/sentry-greptile/pull/2](https://github.com/ai-code-review-evaluation/sentry-greptile/pull/2)
Golden: 3 | Findings: 13 | TP: 2 | FP: 11 | FN: 1 | P=15% R=67% F1=25%

**True Positives:**
- G1 (Critical) → F-01 (behavioral/critical)
  Golden: OptimizedCursorPaginator negative-offset branch slices QuerySet with a negative start index
  Finding: Django AssertionError on negative QuerySet slice in OptimizedCursorPaginator
- G2 (High) → F-02 (behavioral/major)
  Golden: BasePaginator negative-offset branch slices QuerySet with a negative start index
  Finding: Negative offset path introduced in DateTimePaginator affects all users

**False Negatives (missed golden):**
- G3 (High) [type-error]: OptimizedCursorPaginator.get_item_key uses floor/ceil on a datetime key (order_by='-datetime'), causing TypeError.

**False Positives (unmatched findings):**
- F-03 (behavioral/critical): Potential null dereference on organization_context.member
- F-04 (behavioral/major): Hard KeyError on missing end_timestamp_precise from Kafka payload
- F-05 (structural/major): Bare literal 1000 in Lua script (three occurrences, two semantics)
- F-06 (structural/major): enable_advanced_features kwarg likely never reaches paginator constructor
- F-07 (behavioral/minor): zunionstore SUM aggregate corrupts timestamp scores on duplicate spans
- F-08 (structural/minor): Misplaced comment in Cursor constructor describes behavior elsewhere
- F-09 (test-integrity/minor): No test coverage for eviction or ZSET ordering behavior
- F-10 (behavioral/minor): Negative offset exposure in OptimizedCursorPaginator else-branch
- F-11 (behavioral/major): Removed max_segment_spans safety guard from load path
- F-12 (behavioral/major): Fence-post boundary check uses raw offset, not clamped start_offset
- F-13 (behavioral/minor): Undocumented eviction direction preferentially drops child spans

---

### sentry__ai-code-review-evaluation__sentry-greptile__PR3
**feat(upsampling) - Support upsampled error count with performance optimizations** — [https://github.com/ai-code-review-evaluation/sentry-greptile/pull/3](https://github.com/ai-code-review-evaluation/sentry-greptile/pull/3)
Golden: 3 | Findings: 16 | TP: 2 | FP: 14 | FN: 1 | P=12% R=67% F1=21%

**True Positives:**
- G1 (Low) → F-04 (behavioral/minor)
  Golden: sample_rate = 0.0 is falsy and skipped
  Finding: `if client_sample_rate:` drops zero; bare `except Exception: pass`
- G2 (Low) → F-13 (fragile/major)
  Golden: Using Python’s built-in hash() to build cache keys is non-deterministic across processes (hash randomization), so keys w...
  Finding: `hash()` on tuple is PYTHONHASHSEED-randomized; breaks cross-worker cache sharing and invalidation

**False Negatives (missed golden):**
- G3 (Medium) [observability]: The upsampling eligibility check passes the outer dataset instead of the actual dataset used by scoped_dataset. In paths where the query ultimately ru...

**False Positives (unmatched findings):**
- F-01 (fragile/minor): Cache `is not None` sentinel fragility for bool values
- F-02 (behavioral/minor): Substring match `event.type:error` matches negated/partial strings
- F-03 (structural/minor): Column transform called 3x in mutually exclusive branches
- F-05 (test-integrity/major): Test asserts count==10 via indirect sample_weight derivation
- F-06 (test-integrity/minor): No tests for public functions or cache paths
- F-07 (behavioral/major): `upsampled_count` registered only in discover dataset; errors dataset path reachable
- F-08 (structural/minor): Dead variable `should_upsample` aliased to `upsampling_enabled` with misleading comment
- F-09 (behavioral/major): Errors dataset unconditionally triggers upsampling without query check
- F-10 (structural/minor): Docstring says `sum(sample_weight)` but function emits `upsampled_count()` string
- F-11 (test-integrity/major): setUp overwrites `self.user` after `login_as`; `self.authed_user` saved but never used
- F-12 (test-integrity/minor): Comments say "1 event" but assertions check count==10
- F-14 (structural/minor): `_are_all_projects_error_upsampled` accepts `organization` param but never uses it
- F-15 (test-integrity/major): Integration tests mock `options` but don't clear cache; stale cache bypasses mocks
- F-16 (behavioral/minor): `upsampled_count` result type "number" vs `count()` result type "integer"

---

### sentry__getsentry__sentry__PR67876
**GitHub OAuth Security Enhancement** — [https://github.com/getsentry/sentry/pull/67876](https://github.com/getsentry/sentry/pull/67876)
Golden: 3 | Findings: 9 | TP: 2 | FP: 7 | FN: 1 | P=22% R=67% F1=33%

**True Positives:**
- G1 (Medium) → F-06 (behavioral/major)
  Golden: Null reference if github_authenticated_user state is missing
  Finding: get_user_info() unprotected by exception handling
- G3 (High) → F-09 (behavioral/major)
  Golden: The code attempts to access integration.metadata[sender][login] without checking for the existence of the sender key. Th...
  Finding: Unguarded metadata["sender"]["login"] risks KeyError on legacy integrations

**False Negatives (missed golden):**
- G2 (Medium) [type-error]: OAuth state uses pipeline.signature (static) instead of a per-request random value

**False Positives (unmatched findings):**
- F-01 (structural/minor): Bare literal `"github"` replaces named constant
- F-02 (behavioral/major): Redundant Integration query, misleading error for inactive integrations
- F-03 (test-integrity/major): test_installation_not_found tests wrong code path
- F-04 (structural/minor): Broad exception swallow in token exchange
- F-05 (fragile/minor): Hardcoded pipeline signature in 6 test locations
- F-07 (test-integrity/major): test_github_user_mismatch assertion non-discriminating
- F-08 (fragile/major): Hardcoded HMAC likely already invalid, wrong branch exercised

---

### sentry__ai-code-review-evaluation__sentry-greptile__PR5
**Replays Self-Serve Bulk Delete System** — [https://github.com/ai-code-review-evaluation/sentry-greptile/pull/5](https://github.com/ai-code-review-evaluation/sentry-greptile/pull/5)
Golden: 3 | Findings: 8 | TP: 1 | FP: 7 | FN: 2 | P=12% R=33% F1=18%

**True Positives:**
- G3 (Low) → F-02 (structural/major)
  Golden: Using zip(error_ids, events.values()) assumes the get_multi result preserves the input order; dict value order is not gu...
  Finding: Parallel collection coupling in fetch_error_details

**False Negatives (missed golden):**
- G1 (Medium) [api-misuse]: Breaking changes in error response format
- G2 (Medium) [api-misuse]: Detector validator uses wrong key when updating type

**False Positives (unmatched findings):**
- F-01 (behavioral/major): Analytics recorded before feature flag gate
- F-03 (behavioral/minor): Browser report validation allows both age and timestamp absent
- F-04 (structural/minor): Silent error discard in get_environment_info
- F-05 (behavioral/major): TableWidgetVisualization renders empty hardcoded data
- F-06 (behavioral/minor): Grouping variant type row and tooltips removed
- F-07 (structural/minor): Unused attributeKey variable in renamed test
- F-08 (test-integrity/minor): Test type asymmetry in aggregateColumnEditorModal

---

### sentry__getsentry__sentry__PR93824
**Span Buffer Multiprocess Enhancement with Health Monitoring** — [https://github.com/getsentry/sentry/pull/93824](https://github.com/getsentry/sentry/pull/93824)
Golden: 5 | Findings: 9 | TP: 3 | FP: 6 | FN: 2 | P=33% R=60% F1=43%

**True Positives:**
- G1 (Medium) → F-03 (structural/minor)
  Golden: Inconsistent metric tagging with 'shard' and 'shards'
  Finding: Metrics tag key "shard" vs "shards" inconsistency
- G4 (Medium) → F-06 (test-integrity/minor)
  Golden: Sleep in test_consumer.py won’t actually wait because time.sleep was monkeypatched above; consider restoring sleep or us...
  Finding: test_basic time.sleep(0.1) is no-op due to monkeypatch
- G5 (Medium) → F-01 (behavioral/major)
  Golden: Breaking out of the loop when the deadline has elapsed can skip terminating remaining flusher processes, potentially lea...
  Finding: join() skips termination of remaining processes on timeout

**False Negatives (missed golden):**
- G2 (Low) [test-quality]: Fixed sleep in tests can be flaky; wait on condition instead
- G3 (High) [type-error]: Because flusher processes are created via multiprocessing.get_context('spawn').Process, they are instances of multiprocessing.context.SpawnProcess, wh...

**False Positives (unmatched findings):**
- F-02 (structural/minor): Dead method `_create_process_for_shard` (never called)
- F-04 (structural/minor): Docstring claims one-process-per-shard; code caps at max_processes
- F-05 (structural/minor): CLI default=1 makes shard-count fallback dormant via CLI
- F-07 (test-integrity/minor): test_flusher_processes_limit checks structure only
- F-08 (behavioral/minor): Zero-value sentinel ambiguity in max_processes
- F-09 (behavioral/minor): Thread zombie on restart races with replacement on shared Values

---

### sentry__getsentry__sentry__PR77754
**feat(ecosystem): Implement cross-system issue synchronization** — [https://github.com/getsentry/sentry/pull/77754](https://github.com/getsentry/sentry/pull/77754)
Golden: 4 | Findings: 10 | TP: 3 | FP: 7 | FN: 1 | P=30% R=75% F1=43%

**True Positives:**
- G1 (Medium) → F-01 (behavioral/major)
  Golden: Shared mutable default in dataclass timestamp
  Finding: `queued` default evaluated at import time, not instantiation
- G3 (Low) → F-07 (test-integrity/minor)
  Golden: Method name says 'empty_array' but tests empty dict - consider renaming to 'test_from_dict_empty_dict' for clarity.
  Finding: Test name `test_from_dict_empty_array` misleads (tests dict)
- G4 (Medium) → F-02 (behavioral/major)
  Golden: to_dict() returns a datetime for queued; if this dict is passed in task kwargs (e.g., via apply_async), JSON serializati...
  Finding: Celery JSON round-trip corrupts `queued` from datetime to string

**False Negatives (missed golden):**
- G2 (Low) [naming]: The method name has a typo: test_from_dict_inalid_data should be test_from_dict_invalid_data.

**False Positives (unmatched findings):**
- F-03 (structural/minor): `sync_status_outbound` parameter added but never wired
- F-04 (test-integrity/major): No round-trip serialization test
- F-05 (fragile/minor): `from_dict()` silently accepts wrong field types
- F-06 (test-integrity/minor): No direct unit test for `should_sync` cycle prevention
- F-08 (test-integrity/minor): `test_from_dict_valid_data` omits `queued` assertion
- F-09 (test-integrity/major): No deassign cycle-prevention test
- F-10 (behavioral/minor): Silent cycle-guard loss on malformed source dict

---

### sentry__getsentry__sentry__PR80528
**ref(crons): Reorganize incident creation / issue occurrence logic** — [https://github.com/getsentry/sentry/pull/80528](https://github.com/getsentry/sentry/pull/80528)
Golden: 2 | Findings: 8 | TP: 2 | FP: 6 | FN: 0 | P=25% R=100% F1=40%

**True Positives:**
- G1 (High) → F-01 (behavioral/minor)
  Golden: The function modifies the config variable to include display values but then returns the original monitor.config instead...
  Finding: `get_monitor_environment_context` returns original config, discarding modified copy
- G2 (Low) → F-06 (structural/minor)
  Golden: The code fetches MonitorCheckIn objects by ID when the required data already exists in previous_checkins. This creates a...
  Finding: Redundant DB fetch when threshold=1

**False Positives (unmatched findings):**
- F-02 (behavioral/minor): `get_failure_reason` produces broken output when `status_counts` is empty
- F-03 (behavioral/minor): Loop creates N occurrences for N-check-in threshold window
- F-04 (behavioral/minor): `monitor_environment_failed` signal fires unconditionally
- F-05 (behavioral/major): Incident triggers before threshold reached with insufficient history
- F-07 (structural/minor): `get_environment()` called twice in same function
- F-08 (structural/minor): Identical `SimpleCheckIn` dict constructed at two sites

---

### sentry__getsentry__sentry__PR95633
**feat(uptime): Add ability to use queues to manage parallelism** — [https://github.com/getsentry/sentry/pull/95633](https://github.com/getsentry/sentry/pull/95633)
Golden: 3 | Findings: 7 | TP: 1 | FP: 6 | FN: 2 | P=14% R=33% F1=20%

**True Positives:**
- G3 (Low) → F-04 (test-integrity/major)
  Golden: The test test_thread_queue_parallel_error_handling has a docstring that doesn't match the test implementation.
  Finding: Error handling test assertion contradicts stated intent

**False Negatives (missed golden):**
- G1 (High) [null-safety]: The queue.shutdown() method with 'immediate=False' parameter may not exist in the standard Python queue module. This could cause AttributeError at run...
- G2 (Low) [style]: The magic number 50 for max_wait is used repeatedly throughout the tests. Consider extracting this as a named constant to improve maintainability.

**False Positives (unmatched findings):**
- F-01 (structural/minor): Conditional offset registration in submit error handler
- F-02 (structural/minor): Dispatch chain else-pairing fragility
- F-03 (test-integrity/minor): Unit test bypasses +1 Kafka offset convention
- F-05 (test-integrity/minor): Distribution test only checks coverage
- F-06 (behavioral/minor): Backpressure docstring claim vs unbounded queues
- F-07 (structural/minor): Bare literal duplication for default queue count

---

### sentry__getsentry__sentry__PR80168
**feat(workflow_engine): Add in hook for producing occurrences from the stateful detector** — [https://github.com/getsentry/sentry/pull/80168](https://github.com/getsentry/sentry/pull/80168)
Golden: 2 | Findings: 8 | TP: 1 | FP: 7 | FN: 1 | P=12% R=50% F1=20%

**True Positives:**
- G1 (High) → F-01 (structural/major)
  Golden: MetricAlertDetectorHandler inherits from StatefulDetectorHandler but only contains pass, failing to implement its requir...
  Finding: `MetricAlertDetectorHandler` uninstantiable — missing abstract method implementations

**False Negatives (missed golden):**
- G2 (Low) [style]: Docstring says this returns a list of DetectorEvaluationResult, but the method now returns a dict keyed by DetectorGroupKey. Consider updating the doc...

**False Positives (unmatched findings):**
- F-02 (test-integrity/major): Multi-group test builds expected occurrence with wrong `value` (6 vs 10)
- F-03 (test-integrity/minor): Multiple tests build expected occurrences with mismatched `value` parameter
- F-04 (fragile/major): `PriorityLevel(new_status)` relies on implicit integer alignment between independent enums
- F-05 (test-integrity/minor): Removed duplicate-detection test with no replacement for dict uniqueness guarantee
- F-06 (test-integrity/minor): Hardcoded identical UUIDs across all mock occurrences
- F-07 (test-integrity/major): group_key mismatch: occurrence built for `"val1"` but result uses `"group_key"`
- F-08 (test-integrity/major): `build_mock_occurrence_and_event` ignores `value` parameter — root cause of F-02/F-03

---
