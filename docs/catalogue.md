# Catalogue schema and evidence

The four core catalogue data files use schema_version 2. The optional `profiles.json` sidecar introduced in 0.4.0 uses its own schema_version 1. Metadata is independent of the interface language. Model IDs are stable lowercase identifiers; source names, document cover titles and operating-system names retain their factual source designation.

## Models

The model catalogue supplies localized scope text, source definitions and model records. A model has a name, explicit aliases, a family, a coarse catalogue-era label, cited source IDs, an optional observed manufacturer matrix URL, document IDs and driver metadata IDs.

Version 0.2.0 added an optional `thinkwiki` list of `{title, url}` references without changing schema_version 2 or legacy input requirements. Each URL is an explicitly checked HTTPS category on www.thinkwiki.org, not a category inferred at build time from a model ID. All bundled entries carry this field, including an empty list where no category is verified. Missing or empty legacy/reference lists render a model-specific ThinkWiki search, clearly marked as not having a verified dedicated page. Search URLs are constructed locally and require no build-time network access. Grouped source identities can have several links, and type-qualified entries may share a community category without becoming interchangeable hardware or driver targets. ThinkWiki is labelled as a community source; a category can be a stub, and existence does not certify completeness or compatibility. See [data quality and source errata](data-quality.md) for the current coverage method and corrected manufacturer labels.

An ID identifies a documented source entry, not necessarily a unique hardware configuration. Some manufacturer selector labels intentionally group multiple variants or machine types. Preserve qualifiers. Do not silently map a regional/type-qualified model to a different model's document or package.

## Introduction years and timeline navigation

The optional `introduced` model field is a list of `{year, variants, url}` records. Each integer year (1992–2100) needs one or more explicit source-supported variant names and an HTTPS citation. The field does not replace source identity, model associations or the original coarse era. Missing or empty lists mean an unconfirmed introduction year, not an invitation to infer it from driver dates or a nearby model. An optional `introduced_unknown` list names unresolved members of an otherwise partially dated group; that entry remains accessible under unconfirmed dates as well as its documented years.

Version 0.3.2 adds an optional `evidence` object to an introduction row: `{kind, note}`. `kind` is one of `commercial_listing`, `regional_availability`, or `regional_sku_launch`; `note` contains nonempty English and Spanish scope explanations. Unknown fields and evidence kinds are rejected. Existing `{year, variants, url}` rows remain valid. Qualified model pages say “Documented years”, show the localized kind and scope note, and retain the exact source link. A dated commercial brochure can establish that the exact type was documented in that year; a regional SKU listing can establish recorded availability or introduction for that configuration. Neither proves a worldwide first launch. The timeline includes these cited years as documented navigation metadata, with the distinction explained on the model page.

A grouped manufacturer entry can occur in several years when its variants were introduced separately. Year totals count matching catalogue entries, so summing across years can exceed the number of unique model records. A year link is a navigation aid, not hardware compatibility evidence.

Since 0.4.1, catalogue table headers use concise Model, Family, Manuals and Drivers & Software labels in each interface language. ALL-view filter labels use Models, Family, Drivers & Software and Manuals, with concise with/without options; alias matching remains supported. Model aliases and family/era descriptions remain; manual/software cells contain only their original counts and section links. The standalone matching-entry counter is omitted, while year-rail counts and the filtered empty-results message remain. Dark is the initial theme with or without scripts; a valid saved explicit light/dark preference overrides it, not the system theme.

The landing page opens on ALL, the leftmost option before the earliest year. Model/alias search and family/availability filters exist only in that all-model view. Choosing a year clears those filters and hides the form, showing only that year's entries. The native range includes ALL as its first position, then covers the complete earliest-to-latest interval, including empty years. Undated entries remain available under ALL. The year rail keeps touch/keyboard scrolling but hides its native scrollbar, leaving the range control as the visible slider. Plain clicks and keyboard activation smoothly center the selected year within the rail, clamped at the endpoints; reduced-motion preferences and slider scrubbing use immediate scrolling. Only the horizontal rail moves, not page ancestors. Modified clicks preserve native link behavior; there is no separate undated-entry option in the timeline. Every year also has a static HTML page, so year navigation and same-year language switching work without JavaScript or a server. Since 0.4.2, the landing, all-model and year views omit the separate document/utility library. Model-specific manuals and software remain linked from catalogue rows and model pages. The shared footer contains only the independent-community/non-affiliation statement and a localized creator credit linking Mikel Calvo to https://mikelcalvo.net/ in a new tab.

## Navigation and local preferences

The 0.4.3 navigation uses catalogue/source links on the left and a native language picker next to the theme and GitHub controls on the right. A localized Home/Inicio icon precedes the catalogue link on subpages, replacing the separate brand row and back arrow. A relative root SVG favicon is included on every generated page; image admission is restricted to local assets.

Only the neutral root entry follows a saved explicit language choice; without one, the ordinary build starts in English. A build made with `--default-language es` retains its Spanish no-preference fallback. Explicit language URLs are never redirected by that preference. Language switching preserves the model, selected year or sources page and current query/fragment. Storage refusal does not prevent navigation, and the native picker and links work without JavaScript. Theme persistence remains independent.

## Documents and utility references

Document metadata contains a title, source URL, official/community classification, optional observed SHA-256 and size, and a factual model hint. A missing fingerprint means it has not been recorded; it is not an invitation to fabricate one. A hardware service manual and a product specification reference are different document types even when both mention a model.

Utility references identify source instructions or README material, not executable content offered by the site. Project-authored explanations and warnings are localized in the interface rather than embedded in untranslated titles.

## Driver metadata

Driver records describe source-listed package information: title, category, version if known, advertised operating systems, a source date if stated, typed download/README/reference URLs, the source page, evidence level and risk classification. A source digest, when present, fingerprints the source evidence, not necessarily the downloadable installer.

Evidence values:

- manufacturer_listing: advertised on a retained or observed model-source listing. Shared entries and historical listing errors remain possible.
- readme_model_list: an explicit association supported by the package's own model list. Still not proof of installation compatibility.

Risk values separate firmware from other software. Read the exact source instructions before considering any BIOS, embedded-controller or firmware operation. A non-firmware classification is not a guarantee that a package is harmless.

Counts must distinguish source rows, model-route associations, metadata records and distinct download URLs. One shared package can appear in several model routes; do not advertise repeated listing rows as unique installers. Empty driver_ids means the catalogue has not yet indexed package metadata for that entry, not that no driver exists anywhere.

## Source-backed model profiles

The optional `profiles.json` contains `{schema_version: 1, profiles: [...]}` and must contain exactly one audit entry per model ID. Each entry has `model_id`, nullable localized `summary` and `context`, and lists of `facts`, `dates`, `prices`, `markets` and `references`. Empty audit entries are valid; absence of evidence must not be filled by a neighboring identity. Unknown fields, duplicate IDs/keys, unsafe URLs and unresolved reference IDs are rejected before public output is created. Legacy catalogues without this sidecar remain supported by the ordinary builder.

Facts contain `key`, localized `value` and `scope`, and nonempty `sources` reference IDs. Supported keys cover processor, display, memory, storage, graphics, weight, dimensions, ports, connectivity, battery, original operating systems, positioning and features. References contain `id`, HTTPS `url`, `title`, `kind` (`official`, `community` or `press`) and a source `locator`. Narrative-only references are retained too.

Dates preserve year/month/day precision and distinguish `announcement`, `availability`, `sku_announcement` and `documented_by`. Historical prices require a positive decimal-string `amount`, ISO-style three-letter `currency`, dated evidence, localized scope and source IDs; `kind` distinguishes `launch`, `catalogue` and `contemporary_review`. A later catalogue price is not an original launch price. Market entries have localized scope and a nullable boolean `exclusive`: only explicit `true` enables a compact exclusivity label. Regional listings alone do not establish exclusivity.

The public builder validates this sidecar and uses the model-dossier layout with its local stylesheet. Headers show documented event meaning, series, sourced prices and explicit exclusivity only. All technical facts remain in native expandable groups; detailed source scope and citations remain in final references. The profile data does not change timeline identity or document/software associations. Retained source captures and research ledgers are private working evidence, not part of the generated site or repository.

## Safe contributions

Cite the exact source URL and explicit model qualifier. Never infer a new model association from family resemblance. Keep proprietary document/readme bodies and binaries out of source, tests, generated public output and reachable Git history. Tests use minimal synthetic examples rather than reproducing original files.
