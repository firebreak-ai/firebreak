# Spec trim brief

The spec trim runs inside spec close, before the review. Firebreak loads the Trim section below, one sentence per line, as the session's instructions. `{unit}`, `{spec}` and `{guides}` are filled in by Firebreak.

## Trim

You are trimming a draft spec before its review. It is for the {unit} unit in this project. Edit only `{spec}`.
Read first: the human's decisions listed below with their sources, the accepted intent and design listed below, then the spec and the source and tests it refers to.
Each example in the spec becomes at least one test that someone must keep working, so an example that catches no mistake the others miss is cost without benefit. Make the spec state the same agreed behavior with fewer words and fewer examples:
- Keep the fewest examples that tell each rule apart from the ways an implementer is likely to misread or skip it. One example may show several rules. Merge examples that would catch the same wrong implementation, and remove one that catches nothing the rest miss.
- Merge requirements a user would see as one behavior, keeping every link to the design choices they come from.
- Remove text that repeats another document or the examples, and any property, check or detail that neither the human nor an accepted document asks for.
- Remove an example written at an entry point the design does not name, unless it shows an effect the named entry points cannot observe.
Never remove anything a human decision names, from any phase, or the last example of a rule. Keep the link form the spec already uses, any line whose exact form the workflow guides in `{guides}` require (such as a review-only marker), and escape sequences as written. Add nothing.
Reply with the list of what you merged or removed, one entry each with the reason. Firebreak adds that list to the end of the spec under "Removed on purpose", so do not write that section yourself.
