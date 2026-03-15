# Widget Export Feature

## Problem

Users need to export dashboard widgets as PNG and SVG for use in external
reports and presentations. Currently the only option is a manual screenshot,
which loses resolution and omits accessibility metadata. Support tickets
about export have increased 40% quarter-over-quarter.

## Goals

- Provide one-click export of any dashboard widget to PNG or SVG.
- Preserve accessibility metadata (alt text, ARIA labels) in SVG output.
- Support batch export of all widgets on a dashboard.
- Maintain export performance under 2 seconds for typical widget complexity.

## User-facing behavior

When a user hovers over a widget, an export icon appears in the top-right
corner. Clicking the icon opens a dropdown with format options: PNG (raster)
and SVG (vector). Selecting a format triggers an immediate download.

For batch export, the dashboard toolbar includes an "Export All" button that
packages every widget into a ZIP archive. A progress indicator shows
completion percentage during batch operations.

Keyboard users can trigger export via Ctrl+Shift+E when a widget has focus.
Screen readers announce "Export menu" when the icon receives focus.

Export respects the current theme (light/dark) and any applied filters.
Exported files use the naming convention `{dashboard}-{widget}-{timestamp}`.

## Technical approach

The export pipeline has three stages:

1. **Snapshot**: Capture the widget DOM subtree using `html2canvas` for PNG
   and a custom SVG serializer for vector output.
2. **Transform**: Apply resolution scaling (2x for PNG), strip interactive
   event handlers, and inject accessibility attributes into SVG.
3. **Package**: For single exports, trigger a browser download via a Blob URL.
   For batch, use JSZip to assemble the archive client-side.

SVG serialization handles embedded images by inlining them as base64 data
URIs. Font references are converted to embedded `@font-face` declarations.

Performance budget: snapshot + transform must complete within 1.5 seconds for
widgets containing up to 500 DOM nodes.

## Testing strategy

- Unit tests for SVG serializer covering attribute preservation (AC-01).
- Integration test confirming PNG export produces a valid image file with
  correct dimensions, verifying the snapshot pipeline (AC-01).
- End-to-end test for batch export: create a dashboard with 5 widgets,
  trigger Export All, verify ZIP contains 5 files (AC-02).
- Accessibility audit: verify exported SVG includes alt text and ARIA
  attributes from source widget (AC-01, AC-03).
- Performance benchmark: export a 500-node widget, assert < 2 seconds (AC-04).
- Keyboard interaction test: Ctrl+Shift+E triggers export menu (AC-03).

## Documentation impact

- Add "Exporting Widgets" section to the Dashboard User Guide.
- Update API reference with new `exportWidget()` and `exportAll()` methods.
- Add accessibility notes to the Widget Development Guide.

## Acceptance criteria

- **AC-01**: Single widget exports to PNG and SVG with correct content.
- **AC-02**: Batch export produces a ZIP containing one file per widget.
- **AC-03**: Export is accessible via keyboard and screen reader.
- **AC-04**: Export completes within 2 seconds for widgets up to 500 nodes.

## Dependencies

- `html2canvas` v1.4+ (already in bundle).
- `JSZip` v3.10+ (new dependency, ~90 KB gzipped).
- Design team to provide export icon assets by sprint 3.

## Open questions

- Should we support PDF export in the initial release? Deferring keeps scope
  manageable, but sales has flagged PDF as a frequent request.
- How do we handle widgets with real-time data streams during export? Freezing
  the data at snapshot time is simplest, but users may expect live values.
