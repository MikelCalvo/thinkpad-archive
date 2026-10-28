# Catalogue schema and evidence

All public data files use schema_version 2. Metadata is independent of the interface language. Model IDs are stable lowercase identifiers; source names, document cover titles and operating-system names retain their factual source designation.

## Models

The model catalogue supplies localized scope text, source definitions and model records. A model has a name, explicit aliases, a family, a coarse catalogue-era label, cited source IDs, an optional observed manufacturer matrix URL, document IDs and driver metadata IDs.

Version 0.2.0 adds an optional `thinkwiki` list of `{title, url}` references without changing schema_version 2 or legacy input requirements. Each URL is an explicitly checked HTTPS category on www.thinkwiki.org, not a category inferred at build time from a model ID. All bundled entries carry this field: 243 have one or more references (279 links, 272 distinct resolved pages); seven have an empty list. Missing or empty legacy/reference lists render a model-specific ThinkWiki search, clearly marked as not having a verified dedicated page. Search URLs are constructed locally and require no build-time network access. Grouped source identities can have several links, and type-qualified entries may share a community category without becoming interchangeable hardware or driver targets. ThinkWiki is labelled as a community source; a category can be a stub, and existence does not certify completeness or compatibility.

An ID identifies a documented source entry, not necessarily a unique hardware configuration. Some manufacturer selector labels intentionally group multiple variants or machine types. Preserve qualifiers. Do not silently map a regional/type-qualified model to a different model's document or package.

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
