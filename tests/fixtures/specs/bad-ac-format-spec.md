# Search Autocomplete Feature

## Problem

Users type full queries before seeing results, increasing time-to-answer
and causing unnecessary load on the search backend.

## Goals

- Show autocomplete suggestions as the user types.
- Reduce average query length by 30%.

## User-facing behavior

After typing 3 or more characters, a dropdown appears below the search
input with up to 8 suggestions. Arrow keys navigate the list; Enter
selects the highlighted suggestion. Pressing Escape dismisses the dropdown.

## Technical approach

A new `/api/v1/search/suggest` endpoint returns ranked suggestions using
a prefix trie built from historical queries. The frontend debounces input
at 150ms and renders suggestions in a virtualized list component.

Results are cached client-side with a 5-minute TTL keyed by prefix.

## Testing strategy

- Unit tests verify the prefix trie returns correct matches for Criteria-1.
- Integration test confirms API returns suggestions within 100ms for REQ-01.
- End-to-end test validates keyboard navigation per AC1.

## Documentation impact

Update the Search API reference with the new suggest endpoint.

## Acceptance criteria

- **Criteria-1**: Suggestions appear within 200ms of typing 3+ characters.
- **REQ-01**: API returns at most 8 ranked suggestions per prefix.
- **AC1**: Keyboard navigation works with arrow keys and Enter.

## Dependencies

- Elasticsearch 8.x for prefix query support.

## Open questions

- Should we personalize suggestions based on user history? Starting with
  global popularity keeps complexity low while we validate the feature.
