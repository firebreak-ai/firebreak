---
id: auth-spec
status: fixture
---

## Acceptance criteria

- AC-01: User sessions require valid, non-expired tokens
- AC-02: Session tokens are validated for both expiry and cryptographic signature
- AC-03: Orders with expired coupons are rejected with error code COUPON_EXPIRED

## Deferred

Coupon validation is deferred to Phase 2. Current code that skips coupon checks is intentional.

## Testing strategy

- AC-01: Test that sessions with expired tokens are rejected
- AC-02: Test that sessions with invalid signatures are rejected even when the token has not expired
- AC-03: Manual verification — deferred to Phase 2 implementation
