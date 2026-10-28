# [![ThinkPad Archive](docs/readme-header.svg)](https://thinkpadarchive.com/)

**[Browse the archive](https://thinkpadarchive.com/)** · [Build locally](#build-locally) · [Contribute](#contributing) · [MIT license](LICENSE)

Find manuals, driver metadata and source references for documented ThinkPad models, with an emphasis on early machines. The site is available in English and Spanish. You can also build a local copy and browse it without a server.

**v0.3.2 · public preview.** The catalogue and interface are still under development. Coverage is source-grounded, not exhaustive. See the [changelog](CHANGELOG.md) for the current scope.

This is an independent community project, not affiliated with, endorsed by or an official publication of IBM or Lenovo.

## In the catalogue

| Content | Indexed entries |
| --- | ---: |
| Documented model entries | 666 |
| Manual and other document references | 489 |
| Driver/software metadata entries | 14,901 |
| Utility references | 10 |

Model pages collect source-supported names and aliases, document links, driver/software listings and provenance. Start with ALL at the left of the timeline to search the complete catalogue and filter by family or available references. Swipe to a year or use the slider for a clean year-only list without search or filters. Entries with unconfirmed years stay in ALL, without a separate timeline option. Grouped variants may appear in more than one documented year. Package metadata includes advertised operating systems, versions and dates where the source provides them. ThinkWiki links are labelled as community references, with an explicit search fallback when no dedicated page has been verified.

These counts describe catalogue records, not unique working downloads or hardware-tested packages. Manufacturer selectors can group variants, and a shared package can appear on several model routes. Missing information stays missing rather than being inferred from a similar model name. The source-backed timeline now reaches 2026. 665 entries have a documented year, including explicitly qualified regional availability and commercial-listing dates. A22m type 2633 remains undated; 750CSE and 1400/2651 remain unverified selector members. See the [0.3.2 historical backfill](docs/year-backfill-0.3.2.md) for the seven added variant years and their limits, alongside the [data-quality review and explicit selector errata](docs/data-quality.md) and the [catalogue schema and evidence levels](docs/catalogue.md).

### Before installing historical software

Read the exact package README. Check machine type/model (MTM), variant, operating system, architecture, device and dependencies. A source listing does not guarantee that a link is still live or that a package applies to your machine.

**BIOS, embedded-controller, recovery and destructive utilities require separate care.** They are not routine driver updates. The site does not run downloads, automate installation or certify compatibility. Documentation review and content hashes are not hardware tests.

## Build locally

You need Python 3.11 or later. The builder uses only the standard library. From the project directory:

```sh
python3 -m unittest discover -s tests -v
mkdir -p build
python3 -m thinkpad_archive build --output build/public
python3 tools/check_site.py build/public
```

The output destination must not already exist. Open `build/public/index.html` in your browser, including through `file://`. Pages and links work without JavaScript; optional search and filters run on your device. External manual, source and package links still need Internet access. Modern-browser checks do not establish support for every historical browser.

To make Spanish the root language:

```sh
python3 -m thinkpad_archive build --output build/spanish --default-language es
```

Switching languages keeps the current model. Both builds contain metadata and links, not manufacturer documents or installer binaries. The moon/sun control remembers your theme in local browser storage; on a first visit it follows your system preference. GitHub and external references open in a new tab, while catalogue navigation stays in the current one.

## Hosting

The public site is at **[thinkpadarchive.com](https://thinkpadarchive.com/)**. You can host the generated files on a static web server, or use the included Docker setup. See the [deployment guide](docs/deployment.md) for container hosting and Coolify configuration.

## Contributing

Corrections, source links and translations are welcome. Please include the exact model or machine-type qualifier and the source URL; prefer primary manufacturer sources. Keep grouped source identities intact unless a reliable source establishes an individual variant. Do not assign packages by family-name resemblance.

For a new language, add a complete locale JSON with the same keys as the existing languages. Translate project interface text and warnings, while preserving original product titles and operating-system identifiers. Do not redistribute or translate a manufacturer document as part of this project.

Before proposing a release, run the tests and link checker, inspect both languages and narrow layouts, and review the [release checklist](docs/release-checklist.md).

## License and source rights

Original project code, documentation, tests, translations and artwork are available under the [MIT License](LICENSE), copyright 2026 MikelCalvo.

The catalogue publishes factual metadata and source links. It does not mirror manufacturer PDFs, driver binaries, original README bodies or captured websites, and it contains no personal inventory or local-device records. The project license does not grant rights to third-party documents, software, websites or trademarks. Public availability and content hashes are not redistribution permission.

See [sources, attribution and publication boundary](docs/sources-and-rights.md) for the full distinction. ThinkPad, IBM, Lenovo and other product names belong to their respective owners.
