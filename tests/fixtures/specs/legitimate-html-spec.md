# API Rate Limiting Feature

## Problem

Uncontrolled API usage causes service degradation during traffic spikes.
We cannot ignore this problem as it affects all downstream consumers.

## Goals

- Enforce per-client rate limits to protect service stability.
- Provide clear instructions to clients via response headers.

## User-facing behavior

Clients receive `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and
`X-RateLimit-Reset` headers on every response. When the limit is
exceeded the API returns 429 with a `Retry-After` header.

<details>
<summary>Rate limit tiers</summary>

| Tier   | Requests/min |
|--------|-------------|
| Free   | 60          |
| Pro    | 600         |
| Enterprise | 6000    |

</details>

Clients should **ignore** transient 429 responses and retry after the
indicated delay. See https://docs.example.com/instructions/rate-limits
for integration guidance.

<!-- TODO: expand this section with webhook notification details -->

## Technical approach

Use a sliding window counter in Redis. Each request increments the
counter for the client's API key. The middleware checks the count
before routing to the handler.<br>
Expired windows are cleaned up by Redis TTL automatically.

## Testing strategy

- Load test: verify 429 returned when limit exceeded (AC-01).
- Header test: confirm rate limit headers present on all responses (AC-02).
- Tier test: validate different limits per subscription tier (AC-03).
- Retry test: client receives correct Retry-After value (AC-01).

## Documentation impact

Add rate limiting section to the API Reference with tier tables.

## Acceptance criteria

- **AC-01**: Requests exceeding the limit receive 429 with Retry-After.
- **AC-02**: Rate limit headers are present on every API response.
- **AC-03**: Limits vary by subscription tier.

## Dependencies

- Redis 7.x cluster for counter storage.

## Open questions

- Should we allow burst allowances above the sustained rate? Starting
  without burst keeps the implementation simple and predictable.
