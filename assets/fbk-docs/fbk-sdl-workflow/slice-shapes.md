Load condition: routed by the breakdown skill once a slice's test-discipline is known.

## Slice shape routing

When the slice's `test-discipline` field is read, load the matching leaf and apply its guidance to that slice only. Do not load other shape leaves for the same slice.

| Slice test-discipline | Load |
|---|---|
| `new-contract` | `slice-shapes/new-contract.md` |
| `contract-preserving` | `slice-shapes/contract-preserving.md` |
| `contract-evolving` | `slice-shapes/contract-evolving.md` |
| `cross-cutting` | `slice-shapes/cross-cutting.md` |
