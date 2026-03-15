# Internationalization — Phase 1

## Problem

The application only supports English, excluding users who prefer other
languages. Key markets include Japan (日本), Germany (Deutschland), and
France. Customer satisfaction surveys show a 25% drop-off among
non-English speakers — a significant gap we must close.

## Goals

- Support UTF-8 content throughout the rendering pipeline.
- Enable locale switching for UI strings — "Sprache wählen" in German,
  "言語を選択" in Japanese, "Choisir la langue" in French.
- Handle right-to-left text for future Arabic support.

## User-facing behavior

A language selector in the footer lets users choose their locale. All
UI strings update immediately without a page reload. Dates, numbers,
and currencies format according to the selected locale — e.g., €1.234,56
in German vs $1,234.56 in English.

Content like "naïve" and "résumé" renders correctly. Emoji such as 🌍
and 🔧 display inline in notification messages.

## Technical approach

Use `react-intl` for string extraction and formatting. Message files
live in `/locales/{lang}.json`. The build pipeline validates that every
key in `en.json` exists in all other locale files.

For CJK text, ensure line-breaking follows UAX #14 rules. Use
`Intl.Segmenter` for grapheme-aware truncation — never split a
character like "字" mid-byte.

## Testing strategy

- Unit test: locale files contain all keys present in en.json (AC-01).
- Rendering test: CJK characters (日本語テスト) display without
  mojibake (AC-01).
- Format test: dates and numbers match locale conventions (AC-02).
- E2E test: switching locale updates all visible strings (AC-03).

## Documentation impact

Add a "Localization Guide" for translators explaining message format.

## Acceptance criteria

- **AC-01**: UI renders correctly with Latin, CJK, and accented characters.
- **AC-02**: Dates and numbers format per the user's selected locale.
- **AC-03**: Locale switching updates all strings without page reload.

## Dependencies

- `react-intl` v6+ for message formatting.
- Translation vendor contract for initial 3 locales.

## Open questions

- Should we support user-contributed translations? Starting with vendor
  translations ensures quality; community contributions can follow later.
