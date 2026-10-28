# ThinkPad Archive

Find manuals, drivers and source references for documented ThinkPad models, with an emphasis on early machines. The static website is English by default, with a Spanish interface and a translation structure ready for additional languages.

This independent community project is not affiliated with, endorsed by or an official publication of IBM or Lenovo. Product names belong to their respective owners.

## Status

Version: 0.2.0. Pre-1.0 preview; the catalogue and interface are still under development. This source release does not deploy a hosted website. See CHANGELOG.md for the included scope.

The catalogue is source-grounded, not exhaustive. Historical manufacturer selectors can group several variants in one entry. A model identity, a manufacturer's advertised driver listing, a checked download and a successful installation are different facts. Missing metadata stays missing rather than being guessed.

## Build and test

Python 3.11 or later; standard library only. Run from this project directory:

    python3 -m unittest discover -s tests -v
    mkdir -p build
    python3 -m thinkpad_archive build --output build/public
    python3 tools/check_site.py build/public

The destination must not already exist. Open build/public/index.html in a browser. No local server is required. Generated pages are readable without JavaScript; optional search and filters run entirely on your device. Following external manual, source and package links requires Internet access.

To make Spanish the root language:

    mkdir -p build
    python3 -m thinkpad_archive build --output build/spanish --default-language es

A language switch keeps the current model. Both output variants contain metadata and links, not manufacturer files or installer binaries.

For container hosting and push-triggered Coolify deployment, see docs/deployment.md.

## What you can find

- Source-supported model names, variants and aliases.
- Hardware Maintenance Manuals and other document references, identified as such.
- Driver/software listings associated with explicit model source routes, with advertised operating systems, dates and versions when available.
- Source, download and README links, with an evidence-level distinction and firmware warnings.
- ThinkWiki links on every model page: verified category references where available, otherwise an explicitly labelled ThinkWiki search.
- Honest missing-data states, rather than assumed support from a similar model name.

The data schema and source classification are documented in docs/catalogue.md. A catalogue entry does not guarantee that an external link remains live or that a package applies to your exact machine.

## Public content boundary

Original code, translations and tests accompany factual metadata, provenance URLs and optional fingerprints. The repository does not mirror PDFs, driver binaries, original README bodies or captured manufacturer websites. It does not include personal inventories or local-device records.

Source availability is not a redistribution license. See docs/sources-and-rights.md. The owner has not yet selected a license for original project material; do not assume an MIT, GPL or other open-source license grant.

## Contributing information

Prefer primary manufacturer sources. Include the exact model or machine-type qualifier and the source URL. Keep grouped source identities intact unless a reliable source establishes the individual variant. Never assign a package to a model merely because they share a family name.

For new translations, add a complete locale JSON with the same keyset as the existing languages. Original product titles and operating-system identifiers retain their source designation; project interface text and warnings should be translated. Do not modify or redistribute a manufacturer document as a translation of this project.

## Before installing historical software

Read the exact package README. Check machine type/model (MTM), variant, operating system, architecture, device and dependencies. Shared driver listings may contain entries for additional models. BIOS, embedded-controller, recovery and destructive utilities are separate deliberate operations, not routine driver updates.

This website does not run downloads, automate installation or certify compatibility. Documentation review and content hashes are not hardware tests. Modern-browser checks do not establish support for every historical browser.

## Release acceptance

Run the complete tests, verify generated internal links, inspect both languages and narrow layouts in a real browser, review provenance and the public file allowlist, then freeze an accepted source version. Public repository creation, push and release publication occur only after the owner has selected the target and reviewed the candidate. See docs/release-checklist.md.
