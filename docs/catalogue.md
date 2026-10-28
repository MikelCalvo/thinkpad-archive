# Catalogue schema and evidence

All public data files use schema_version 2. Metadata is independent of the interface language. Model IDs are stable lowercase identifiers; source names, document cover titles and operating-system names retain their factual source designation.

## Models

The model catalogue supplies localized scope text, source definitions and model records. A model has a name, explicit aliases, a family, a coarse catalogue-era label, cited source IDs, an optional observed manufacturer matrix URL, document IDs and driver metadata IDs.

Version 0.2.0 added an optional `thinkwiki` list of `{title, url}` references without changing schema_version 2 or legacy input requirements. Each URL is an explicitly checked HTTPS category on www.thinkwiki.org, not a category inferred at build time from a model ID. All bundled entries carry this field, including an empty list where no category is verified. Missing or empty legacy/reference lists render a model-specific ThinkWiki search, clearly marked as not having a verified dedicated page. Search URLs are constructed locally and require no build-time network access. Grouped source identities can have several links, and type-qualified entries may share a community category without becoming interchangeable hardware or driver targets. ThinkWiki is labelled as a community source; a category can be a stub, and existence does not certify completeness or compatibility. See [data quality and source errata](data-quality.md) for the current coverage method and corrected manufacturer labels.

An ID identifies a documented source entry, not necessarily a unique hardware configuration. Some manufacturer selector labels intentionally group multiple variants or machine types. Preserve qualifiers. Do not silently map a regional/type-qualified model to a different model's document or package.

## Introduction years and timeline navigation

The optional `introduced` model field is a list of `{year, variants, url}` records. Each integer year (1992–2100) needs one or more explicit source-supported variant names and an HTTPS citation. The field does not replace source identity, model associations or the original coarse era. Missing or empty lists mean an unconfirmed introduction year, not an invitation to infer it from driver dates or a nearby model. An optional `introduced_unknown` list names unresolved members of an otherwise partially dated group; that entry remains accessible under unconfirmed dates as well as its documented years.

A grouped manufacturer entry can occur in several years when its variants were introduced separately. Year totals count matching catalogue entries, so summing across years can exceed the number of unique model records. A year link is a navigation aid, not hardware compatibility evidence.

The landing page opens on ALL, the leftmost option before the earliest year. Model/alias search and family/availability filters exist only in that all-model view. Choosing a year clears those filters and hides the form, showing only that year's entries. The native range includes ALL as its first position, then covers the complete earliest-to-latest interval, including empty years. Undated entries remain available under ALL. The year rail keeps touch/keyboard scrolling but hides its native scrollbar, leaving the range control as the visible slider; there is no separate undated-entry option in the timeline. Every year also has a static HTML page, so year navigation and same-year language switching work without JavaScript or a server. The document/utility library remains available in a native collapsible section.

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

## Safe contributions

Cite the exact source URL and explicit model qualifier. Never infer a new model association from family resemblance. Keep proprietary document/readme bodies and binaries out of source, tests, generated public output and reachable Git history. Tests use minimal synthetic examples rather than reproducing original files.
