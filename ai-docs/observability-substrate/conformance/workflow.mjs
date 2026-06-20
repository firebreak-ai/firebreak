/**
 * Conformance workflow — observability substrate end-to-end test bed.
 *
 * Purpose: exercise the full substrate spine (descriptor → harvest → record →
 * reader) in a single minimal run.  Three agents, two cardinalities, two
 * stances.  This is a slice artifact — not a shipped Firebreak ceremony.
 *
 * Unit map:
 *   implement   single    collaborative   fbk-implementer
 *   test-review fan-out   collaborative   test-reviewer
 *   code-review fan-out   adversarial     code-review-detector
 *
 * The implement unit runs as a lone agent() call (single cardinality).
 * The two review units run inside one parallel([...]) call (fan-out cardinality).
 *
 * Verification: task-17 manual procedure.  After the run closes, run
 *   fbk.py run-retro <run-id>
 * and confirm three units with non-null shape, the cardinalities and stances
 * above, and a populated persona for each.
 */

export const meta = {
  name: 'conformance-e2e',
  description: 'Minimal three-agent spine test: one single implement + two fan-out reviews (one adversarial)',
  phases: [
    { title: 'Implement', detail: 'fbk-implementer: add a single trivial utility function' },
    { title: 'Review', detail: 'test-reviewer + code-review-detector run in parallel; one collaborative, one adversarial' },
  ],
}

// ---------------------------------------------------------------------------
// Descriptor-building glue.
//
// Prepend <!--fbk-attr {json}--> to every agent prompt so the harvest engine
// can read cardinality, stance, and persona from the first transcript message
// without asking the agent what it did.
//
// Key names must match exactly what fbk/attribution.py parses:
//   cardinality   – "single" | "fan-out"   (parsed.get("cardinality"))
//   stance        – "collaborative" | "adversarial"  (parsed.get("stance"))
//   asset_bundle  – object; .persona is used for shape resolution
//                   (parsed.get("asset_bundle") → raw_asset_bundle.get("persona"))
// ---------------------------------------------------------------------------

/**
 * Build the <!--fbk-attr {json}--> sentinel block for one agent.
 *
 * @param {"single"|"fan-out"} cardinality
 * @param {"collaborative"|"adversarial"} stance
 * @param {string} persona  The agentType value for this unit.
 * @returns {string}  The complete sentinel block, terminated with a newline.
 */
function attrBlock(cardinality, stance, persona) {
  const descriptor = {
    cardinality,
    stance,
    asset_bundle: {
      instructions: null,
      persona,
      decision_tree: null,
    },
  }
  return `<!--fbk-attr ${JSON.stringify(descriptor)}-->\n`
}

/**
 * Prepend the attribution sentinel to a prompt string.
 *
 * @param {string} cardinality
 * @param {string} stance
 * @param {string} persona
 * @param {string} body  The actual task prompt.
 * @returns {string}
 */
function withAttr(cardinality, stance, persona, body) {
  return attrBlock(cardinality, stance, persona) + body
}

// ---------------------------------------------------------------------------
// Task content.
//
// The implement unit adds a single trivial helper function to a scratch file
// so the two review units have real (but minimal) artifact content to read.
// The file is a plain text scratch pad so no test suite is exercised here —
// the workflow closes quickly and the record stays legible.
// ---------------------------------------------------------------------------

const REPO = '/home/rahvin/context-assets'
const SCRATCH_FILE = `${REPO}/ai-docs/observability-substrate/conformance/scratch.py`

const IMPL_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['file', 'functionAdded', 'summary'],
  properties: {
    file: { type: 'string' },
    functionAdded: { type: 'string', description: 'name of the function added' },
    summary: { type: 'string' },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['verdict', 'findings', 'summary'],
  properties: {
    verdict: { type: 'string', enum: ['accepted', 'needs-revision'] },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['description', 'severity'],
        properties: {
          description: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
    summary: { type: 'string' },
  },
}

// ---------------------------------------------------------------------------
// Phase 1: Implement (single, collaborative, fbk-implementer)
// ---------------------------------------------------------------------------

phase('Implement')

const implPrompt = withAttr(
  'single',
  'collaborative',
  'fbk-implementer',
  `Write a single trivial Python helper function into the scratch file at ${SCRATCH_FILE}.

The function must be named \`clamp(value, lo, hi)\` and return \`value\` clamped to the range [lo, hi].  Add a one-line docstring.  Write ONLY that function — no imports, no tests, no other code.

Create the file if it does not exist; overwrite it if it does.  Do not git commit.  Report the file path and the function name.`
)

const impl = await agent(implPrompt, {
  label: 'implement:clamp',
  phase: 'Implement',
  schema: IMPL_SCHEMA,
  agentType: 'fbk-implementer',
})

// ---------------------------------------------------------------------------
// Phase 2: Review (fan-out × 2; one collaborative, one adversarial)
//
// Both review units launch inside one parallel([...]) call so each carries
// fan-out cardinality in the record.
// ---------------------------------------------------------------------------

phase('Review')

const testReviewPrompt = withAttr(
  'fan-out',
  'collaborative',
  'test-reviewer',
  `Read the file at ${SCRATCH_FILE}.  It should contain exactly one function named \`clamp(value, lo, hi)\` with a docstring.

Assess whether the implementation is correct and complete for its stated purpose: clamping a value to a [lo, hi] range.  A collaborative review looks for what is there and whether it is sound, not for reasons to reject.

Return verdict "accepted" if the function is correct and has a docstring.  Return "needs-revision" only if there is a clear correctness problem.  Report any findings with severity.`
)

const codeReviewPrompt = withAttr(
  'fan-out',
  'adversarial',
  'code-review-detector',
  `Read the file at ${SCRATCH_FILE}.  It should contain a \`clamp(value, lo, hi)\` function.

You are an adversarial reviewer: your role is to find every flaw, edge case, missing guard, or style violation you can.  Look for: missing docstring, incorrect boundary handling (open vs closed bounds), no type hints, no handling of lo > hi, no handling of non-numeric inputs, any other weakness.

Return verdict "needs-revision" unless the implementation is genuinely flawless.  Report every finding you can find, even low-severity ones.`
)

const [testReview, codeReview] = await parallel([
  () => agent(testReviewPrompt, {
    label: 'review:test',
    phase: 'Review',
    schema: REVIEW_SCHEMA,
    agentType: 'test-reviewer',
  }),
  () => agent(codeReviewPrompt, {
    label: 'review:adversarial',
    phase: 'Review',
    schema: REVIEW_SCHEMA,
    agentType: 'code-review-detector',
  }),
])

// ---------------------------------------------------------------------------
// Aggregate result
// ---------------------------------------------------------------------------

return {
  implement: impl,
  testReview,
  codeReview,
}
