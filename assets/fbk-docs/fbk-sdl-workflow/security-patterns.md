# Security Detection Targets

Apply these detection targets to all code reviews.

1. **Unescaped user input interpolated into HTML, SQL, shell, or template output** — User-supplied or persisted-user-origin values are concatenated into an HTML, SQL, shell, or template string without escaping for the destination grammar. Check for string concatenation, f-strings, template literals, or `<%=` style interpolation where an operand traces back to request input, database fields populated from request input, or unescaped helper output.

2. **Unvalidated URL fetched by server-side code** — An HTTP, file, or open call uses a URL derived from request input without an allowlist or scheme/host validation. Check for `urllib`, `requests`, `http.get`, `fetch`, `open`, `Net::HTTP`, or equivalent calls whose URL argument traces back to a request parameter without passing through a validating wrapper or allowlist check.

3. **Origin validation accepting user-controlled or overly broad values** — Origin checks, `postMessage` `targetOrigin`, CORS allowlists, or referer validation use a value that can be user-supplied or is broader than the intended trust boundary (full URL instead of origin, `*` wildcard, empty string fallback, referer-header trust). Check for `targetOrigin`, `Access-Control-Allow-Origin`, referer comparisons, or framing decisions built from request-derived values.

4. **Disabled or weakened browser security header** — Headers such as `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, and `X-Content-Type-Options` are set to permissive values (`ALLOWALL`, `unsafe-inline`, missing `frame-ancestors`) or removed outright. Check for response-header writes whose value loosens the default browser protection.

5. **Non-deterministic key derivation for cross-process state** — Cache keys, signatures, or dedup identifiers are built from values that are not stable across processes or invocations: Python's built-in `hash()` (randomized per process), `Object.hashCode()`, pointer addresses, iteration order of unordered collections, non-serialized timestamps. Check for cache-key, signature, or identifier construction that calls `hash()`, `hashCode()`, `id()`, or relies on dict/set iteration order.
