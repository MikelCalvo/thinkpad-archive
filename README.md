# [![ThinkPad Archive](docs/readme-header.svg)](https://thinkpadarchive.com/)

[Browse the archive](https://thinkpadarchive.com/) · [Download an offline copy](https://github.com/MikelCalvo/thinkpad-archive/releases) · [Documentation](docs/README.md) · [Contribute](#contributing)

Manuals, driver references and documented history for ThinkPad computers, from early IBM machines to current Lenovo models. Browse in English or Spanish, search by model or alias, and follow each entry back to its sources.

ThinkPad Archive is an independent community project. It is not affiliated with or endorsed by IBM or Lenovo.

## Find your model

Open [thinkpadarchive.com](https://thinkpadarchive.com/) and search the complete catalogue from **ALL**. Filter by family, manuals or software, or choose a documented year on the timeline. Each model page brings together:

- Source-backed technical specifications, historical context and dated evidence where available.
- Manuals, specification sheets and other document references.
- Searchable driver/software listings with source-advertised operating systems and versions.
- Separate firmware listings and installation cautions.
- Source citations and a link to propose a correction.

Search and filters run locally in your browser. Share a filtered catalogue URL or switch languages without losing the current model or year. Basic pages and links work without JavaScript.

## Catalogue coverage

| Content | Records |
| --- | ---: |
| Documented model entries | 666 |
| Manual and other document references | 489 |
| Driver/software metadata entries | 14,901 |
| Utility references | 10 |

There are 665 technical profiles and 7,095 sourced facts. The timeline reaches 2026; 665 model entries have a documented year. These totals count catalogue records, not unique hardware configurations, installers or working downloads. Manufacturer support listings sometimes group several variants.

Coverage is not exhaustive. Missing facts stay missing: X201si has no resolved technical profile, A22m type 2633 remains undated, and some historical selector names are explicitly unverified. Regional availability, SKU announcements and later catalogue prices are labelled rather than presented as worldwide launch facts. See [data quality and known gaps](docs/data-quality.md) and [the catalogue schema](docs/catalogue.md).

[External-link checks](docs/link-checks.md) describe the dated availability audit and its limits. A reachable link is not a compatibility or safety certification.

## Take the catalogue offline

Use the download menu on the website, or get the ZIP and its checksum from [GitHub Releases](https://github.com/MikelCalvo/thinkpad-archive/releases). Extract the whole folder and open `index.html`. You do not need Python, an account or a local server. Both languages are included.

The website shows the actual archive size and a selectable SHA-256, with a copy button when JavaScript is available. Release ZIPs also have a sibling `.zip.sha256` file and an internal `SHA256SUMS.json` manifest.

The offline copy includes catalogue pages, technical profiles and local interface assets. Manufacturer PDFs, installers and live statistics are not bundled; external references still need Internet. The extracted catalogue does not collect analytics or contain nested ZIP downloads.

A checksum detects changed bytes. It does not authenticate the publisher if an attacker can replace both the archive and its advertised hash.

## Before installing software

Read the exact package README and check your machine type, variant, operating system, architecture, device and dependencies. A manufacturer listing or a matching model name does not prove that a package applies to your machine.

**BIOS, embedded-controller, recovery and destructive utilities need particular care.** The archive does not run installers, automate firmware updates or certify hardware compatibility. An available download is not a tested installation.

## Build locally

The builder needs Python 3.11 or later and uses only the standard library. From a checkout of this repository:

```sh
mkdir -p build
python3 -m thinkpad_archive build --output build/public
python3 tools/check_site.py build/public
python3 tools/check_seo.py build/public
```

Open `build/public/index.html`, including through `file://`. Choose a new output directory for each build. Add `--default-language es` for a Spanish root page; either build includes both languages.

To generate the offline distribution:

```sh
mkdir -p dist
python3 -m thinkpad_archive offline-release --output dist/offline
```

For tests, CI, source audits and release instructions, see [development](docs/development.md) and [releases](docs/releases.md). For static or Docker hosting, see [deployment](docs/deployment.md).

## Public statistics and privacy

The hosted [Stats dashboard](https://thinkpadarchive.com/en/stats.html) separates JavaScript page views, full catalogue ZIP transfers and HTML document requests. HTML traffic is estimated as browser-like, declared crawler/automation or unknown. Neither browser-like traffic nor a crawler name verifies who made a request; the figures are not unique visitors.

Collection is an explicit hosting option. Normal static builds and offline copies collect nothing. The optional service stores only public daily aggregate counters, without visitor IDs, cookies, stored IPs, raw user agents or cross-page tracking, and respects DNT/GPC. Existing theme and language preferences stay local to the browser. Infrastructure logs have their own boundary. Read [what is counted and stored](docs/statistics.md) before interpreting the numbers or deploying the service.

## Contributing

Use **Suggest a correction** below a model overview, or [open an issue](https://github.com/MikelCalvo/thinkpad-archive/issues). Include the exact model or machine type, the proposed change and a supporting source, preferably from the manufacturer. Do not include serial numbers or personal information. The model link prepares a GitHub draft; you review and submit it yourself.

Source links, corrections and translations are welcome. Preserve exact variant qualifiers and original product/OS names. Do not infer driver associations from family resemblance or submit copied manufacturer documents or installers. See [safe contributions](docs/catalogue.md#safe-contributions).

## License and source rights

Original code, documentation, translations and artwork are licensed under [MIT](LICENSE), copyright 2026 MikelCalvo. Manufacturer documents, software and trademarks retain their own rights. The project publishes factual metadata and links, not a mirror of those materials. See [sources and rights](docs/sources-and-rights.md).
