# Changelog

## 0.3.0

- Public HTTP-origin container deployment for Coolify, with HTTPS and certificates managed by the external reverse proxy.
- GitHub repository shortcut and a moon/sun theme toggle at the right of the navigation; language links remain on the left.
- Local dark/light preference, an initial system-theme default and a readable system-theme fallback without JavaScript.
- External references, including PDF links, open in a new tab with opener and referrer isolation. Internal navigation stays in the current tab.
- Timeline navigation with ALL first at the left, followed by the calendar years. Search and family/availability filters appear only under ALL; choosing a year clears them and shows only that year's list. A native slider and static HTML links cover both modes. The full reference library is collapsed by default instead of extending the landing page.
- No repeated selected-year caption below the timeline; selection remains highlighted and named for assistive technology.
- Minimal landing layout: project title directly followed by the timeline, without summary counters, numbered section headings or the hero divider.
- Kept the range slider while hiding the duplicate year-rail scrollbar; undated entries remain under ALL without an extra timeline option.
- Source-linked introduction years span 1992–2024 across 237 dated entries. Thirteen entries remain wholly undated and one grouped entry retains an undated variant. Package dates are never used as model launch dates.
- Removed the decorative red strip from the top edge of the page; dark-theme accents remain red rather than pink.
- Refreshed README with an original red-dot wordmark header and an MIT license for original project material. Third-party source and trademark rights remain separate.

## 0.2.0

### Added

- ThinkWiki access on all 250 model pages in English and Spanish, placed beside the model identity.
- 279 explicit category-reference links across 243 catalogue entries, resolving to 272 distinct ThinkWiki pages checked through its public MediaWiki API.
- Separate links for source-grouped models, exact Tablet variants and observed ThinkWiki naming differences.
- A clearly labelled ThinkWiki search for seven entries without a verified dedicated category: Edge E31, P1 Gen 7, Reserve Edition, S51, T14 Gen 5 (AMD), X1 Carbon Gen 12 and X200si. Search access is not presented as a model article.
- Validation and regression tests for explicit community references and safe search fallback. Original model identities, document associations and driver associations are unchanged.

This remains a pre-1.0 preview. ThinkWiki references are community material and do not establish hardware compatibility; category existence checks do not certify every statement on the destination page.

## 0.1.0

Initial pre-1.0 source preview. No hosted website or manufacturer-file mirror is included.

### Included

- Static manual and driver-reference finder with English as the default language and a Spanish interface.
- 250 documented model identities, 88 document references and 10 utility references.
- 14,901 driver metadata entries associated with 129 models, containing 2,096 distinct download URLs and 1,503 distinct README URLs. These are source records and URL counts, not verified unique executable packages.
- Model and alias search, family filters and manual/driver metadata-presence filters, all local to the browser.
- Per-model driver categories with icons, counts and direct navigation, plus separate BIOS/firmware warnings.
- Same-model language switching, narrow-screen layouts and readable static content without JavaScript or a local server.
- Simplified navigation and a large project title with a red dot on the native i glyph.
- Strict public-data validation, safe HTML escaping, synthetic regression fixtures and an internal-link checker.

### Limitations

- The catalogue is not exhaustive. Metadata and source links do not certify package availability, exact hardware compatibility or successful installation.
- No PDFs, driver binaries, original README bodies, private inventories or physical-media records are distributed.
- Mirrors and hosting remain deferred. This version does not configure the project domain or download or run historical software.
- A license for original project code and documentation has not yet been selected. Third-party rights remain unaffected.
