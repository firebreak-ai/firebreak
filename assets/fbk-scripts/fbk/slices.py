"""Shared slice-discipline constants for gate validation."""

TEST_DISCIPLINES = ("new-contract", "contract-preserving", "contract-evolving", "cross-cutting")

# Work-unit structure per shape, as declared in fbk-sdl-workflow/slice-shapes/<shape>.md.
# The breakdown gate uses these in place of its generic has_test/has_impl checks whenever
# every task covering an AC carries a slice_shape.
#
#   new-contract        test task AND impl task
#   contract-evolving   new test tasks AND impl task — the contract is the edge of the
#                       function, so a change to it always moves an argument in or out
#                       and always carries test work
#   contract-preserving impl task only — the contract is unchanged, so no new tests
#   cross-cutting       seam tests only — the implementation lives in other slices
SHAPES_REQUIRING_TEST = frozenset({"new-contract", "contract-evolving", "cross-cutting"})
SHAPES_REQUIRING_IMPL = frozenset({"new-contract", "contract-evolving", "contract-preserving"})
