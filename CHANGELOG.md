# Changelog

## 0.5.0

- Add a public EN/ES statistics dashboard and a compact Stats link beside the creator credit. Keep the header title-only, with an icon refresh action and the archive red-dot treatment in Estadísticas.
- Store only daily marginal page-view counters in first-party SQLite: page, referral category, coarse device/browser/system and page language. No cookies, visitor identifiers, raw referrers or user agents, IP storage, GeoIP, sessions or unique-visitor claims. Respect DNT and Global Privacy Control.
- Retain aggregate history indefinitely. Add All time / Todo el tiempo alongside 7/30/90/365-day views; period filters never delete history. Publish every retained aggregate field through the public API without a dashboard download block.
- Exclude the dashboard and catalogue filter changes from collection. Keep normal static/offline builds collection-free unless explicitly enabled.
- Add opt-in same-origin Caddy/API Docker targets, private persistent count storage and deployment/privacy documentation. Preserve existing catalogue data, software filters, firmware warnings and sharing behavior.

## 0.4.4

- Add software-only package search and a source-listed operating-system filter on model pages, retaining original package wording, evidence, category controls and separate firmware warnings.
- Keep catalogue search, family, availability filters and selected year in shareable URLs, with reload and browser history restoration.
- Use the default index as the complete catalogue for ALL and language navigation; retain catalogue.html for old bookmarks.
- Add localized static Open Graph/X sharing metadata, page-specific titles and descriptions, canonical URLs and two original 1200×630 PNG sharing cards.
- Preserve static no-script/file browsing, all catalogue/profile records and external package associations.

## 0.4.3

- Add an original red pointing-stick SVG favicon to every page.
- Place catalogue/source navigation on the left and a native globe language picker beside the theme and GitHub controls. Remember explicit language choices for the neutral entry while preserving explicit-language deep links and model/year/source context.
- Replace the redundant subpage wordmark and back-to-catalogue arrow with a compact, localized home icon in the navigation row. Retain native no-script language links and tolerate unavailable browser storage.
- Redesign Sources/Fuentes around IBM/Lenovo, PSREF and ThinkWiki entry points, three concise evidence definitions and a visible installation/firmware caution. Keep all original source titles and URLs in grouped native disclosures, alongside coverage and methodology.
- Preserve model/profile data, document/software associations, theme behavior and offline/no-script browsing. Admit only the original favicon SVG in the Docker asset allowlist.

## 0.4.2

- Remove the document and utility library from the landing, all-model and year catalogue pages. Keep catalogue navigation, filtering and model-specific manual/software links unchanged.
- Simplify the shared EN/ES footer to the independent-community/non-affiliation statement and a localized creator credit. Link Mikel Calvo to https://mikelcalvo.net/ in a new tab with noopener noreferrer.
- Preserve catalogue/profile data, model identities, document/software associations, detail-page content and firmware warnings. Existing public metadata inputs remain supported.

## 0.4.1

- Start in dark mode when no valid local preference is saved, regardless of system theme. Keep explicit light/dark choices, cross-tab preference synchronization and a usable toggle when storage is blocked; no-script pages also default to dark.
- Shorten catalogue headings to Model, Family, Manuals and Drivers & Software (and their Spanish equivalents). Use the same concise wording for ALL-view filter labels and options, with Models as the search label while preserving alias search. Keep model aliases and family/era context in rows, while showing only counts and existing section links in the two support columns.
- Remove the repeated matching-entry counter beneath the filters. Keep year-selector counts, search, combined filters, reset, static year links and the empty-results state working without that DOM element.
- Preserve all catalogue/profile data, model identities, manual/software associations, detail-page layout and firmware warnings.

## 0.4.0

- Research-audited all 666 catalogue identities and added a separately validated EN/ES profile sidecar: 665 source-backed summaries and technical profiles, 7,095 technical facts, 652 historical contexts, 652 profiles with dated evidence and 239 with historical prices. X201si remains explicitly unresolved; missing facts are not inferred from neighboring models.
- Integrate the approved model-page design into the ordinary public builder: compact wrapping date/series metadata, historical prices only when sourced, and market labels only for explicitly documented exclusivity. Preserve announcement, availability, exact-SKU and catalogue-price meanings and full scope in the final references.
- Replace the dense specification sidebar with four native collapsed groups that expand to full width. Make historical context optional and collapsible, keep source qualifications at the end, and retain the red dot on the normal ThinkPad “i”. Remove local-preview labels and their footer.
- Retain all model IDs, document/driver associations, package metadata, external links and firmware warnings. Compact manuals and software lists without removing their provenance or native no-script controls. Legacy input without a profile sidecar remains supported.
- Keep the site static, offline-readable and bilingual; publish factual metadata and citations only, not retained research captures, manufacturer documents or installer binaries.

## 0.3.3

- Center the selected year within the horizontal timeline after a plain click or keyboard activation, revealing adjacent years for successive navigation. Animate clicks smoothly unless reduced motion is requested; clamp at either end and return to the left edge for ALL.
- Keep scrolling confined to the year rail so selecting a year does not move the page vertically. Slider scrubbing remains immediate, and modified/middle clicks retain native link behavior.

## 0.3.2

- Researched the eight previously unresolved entries/groups and added seven exact variant years across five catalogue records: R52 types 1850/1870/1862/1863 (2005), Edge E31 Chinese SKU 025027C (2011), X200si Dutch SKU NS2FVMH (2010), and X230i Tablet German campus SKU 3438-AK8 (2012).
- Added optional typed date evidence with localized scope notes. Model pages distinguish a dated commercial listing, a regional SKU introduction and regional availability from a confirmed first launch; these years remain useful timeline navigation metadata.
- The catalogue remains at 666 entries and 489 document references; 665 entries now have at least one documented year. A22m type 2633 remains undated, and 750CSE/1400 type 2651 remain unverified selector members. No dates are inferred from driver releases or manual copyright.
- Preserved all document/driver metadata and model associations. Added source-linked research notes and regressions for the qualified date schema, safe rendering and exact-type backfill. See [the detailed evidence review](docs/year-backfill-0.3.2.md).

## 0.3.1

- Audited the complete previous 250-entry snapshot and compared every dated ThinkWiki History token plus the captured current/withdrawn PSREF laptop, tablet and mobile-workstation index.
- Added 417 source-backed model entries and removed one misclassified desktop, bringing the catalogue from 250 to 666 entries. Document references increase from 88 to 489; 662 entries have at least one documented introduction year.
- Expanded modern, regional, tablet and workstation coverage with exact generation and processor variants, source-linked introduction years and verified manufacturer PDF references. The timeline now spans 1992–2026; new references are not inferred driver associations.
- Strengthened 81 existing introduction citations with exact official PSREF page anchors, and backfilled documented historical and regional years without spreading a family year to unproven machine types.
- Corrected i Series 1800 type 2632 and i Series 1124 to 2000, separated A22m type 2633 from the existing A22p type 2629 identity, and retained the original support-route provenance.
- Removed the S51 selector contamination, positively identified as a ThinkCentre desktop. Preserved the 750CSE and 1400/2651 strings as unverified source members rather than confirmed product aliases.
- Four exact identities remain wholly undated: A22m type 2633, Edge E31, X200si and X230i Tablet. Four dated groups retain unresolved members. Missing years are never filled from driver dates or manual copyright.
- Added explicit offline selector errata, source-quality documentation and data regression checks. Existing driver metadata and all retained-model driver associations are unchanged; no PDFs, source bodies or installers are mirrored.

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
