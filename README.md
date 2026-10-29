# [![ThinkPad Archive](docs/readme-header.svg)](https://thinkpadarchive.com/)

**[Browse the archive](https://thinkpadarchive.com/)** · [Build locally](#build-locally) · [Contribute](#contributing) · [MIT license](LICENSE)

Find manuals, driver metadata and source references for documented ThinkPad models, with an emphasis on early machines. The site is available in English and Spanish. You can also build a local copy and browse it without a server.

**Development version 0.5.5; latest tagged release: v0.5.0.** This version keeps disposable Docker-build test databases in memory to avoid overlay-storage latency, without changing runtime statistics storage or timeout limits. Version 0.5.4 added technical search metadata, crawler discovery files and SEO checks to the existing CI, correction links and offline distributions. Public first-party aggregate statistics, software search and shareable catalogue views remain available. The catalogue is still under development; coverage is documented, not exhaustive. See the [changelog](CHANGELOG.md) for the current scope.

This is an independent community project, not affiliated with, endorsed by or an official publication of IBM or Lenovo.

## In the catalogue

| Content | Indexed entries |
| --- | ---: |
| Documented model entries | 666 |
| Manual and other document references | 489 |
| Driver/software metadata entries | 14,901 |
| Utility references | 10 |

Model pages now include sourced EN/ES summaries, historical context and technical specifications in native collapsible groups. The 666-entry research audit supplies 665 technical profiles and 7,095 facts; 652 profiles contain dated evidence and 239 contain historical prices. These are coverage counts, not worldwide first-launch or universal-price claims. X201si remains unresolved. Compact header metadata omits unsourced prices and shows a market only when exclusivity is explicitly documented; complete source scope remains at the end of each page.

Model pages collect source-supported names and aliases, document links, driver/software listings and provenance. The landing page focuses on the catalogue, without a separate document/utility library. The shared footer contains the independent-community/non-affiliation statement and a creator link to Mikel Calvo. Start with ALL at the left of the timeline to search the complete catalogue and filter by family or available references. Swipe to a year or use the slider for a clean year-only list without search or filters. Entries with unconfirmed years stay in ALL, without a separate timeline option. Grouped variants may appear in more than one documented year. Package metadata includes advertised operating systems, versions and dates where the source provides them. ThinkWiki links are labelled as community references, with an explicit search fallback when no dedicated page has been verified.

These counts describe catalogue records, not unique working downloads or hardware-tested packages. Manufacturer selectors can group variants, and a shared package can appear on several model routes. Missing information stays missing rather than being inferred from a similar model name. The source-backed timeline now reaches 2026. 665 entries have a documented year, including explicitly qualified regional availability and commercial-listing dates. A22m type 2633 remains undated; 750CSE and 1400/2651 remain unverified selector members. See the [0.3.2 historical backfill](docs/year-backfill-0.3.2.md) for the seven added variant years and their limits, alongside the [data-quality review and explicit selector errata](docs/data-quality.md) and the [catalogue schema and evidence levels](docs/catalogue.md).

The Sources page groups IBM/Lenovo documentation, PSREF specifications and ThinkWiki community research into compact entry points. Short evidence definitions and an installation/firmware caution stay visible; the original reference list and coverage/methodology remain available in native disclosures. Source-specific qualifications stay on each model page.

### Before installing historical software

Read the exact package README. Check machine type/model (MTM), variant, operating system, architecture, device and dependencies. A source listing does not guarantee that a link is still live or that a package applies to your machine.

**BIOS, embedded-controller, recovery and destructive utilities require separate care.** They are not routine driver updates. The site does not run downloads, automate installation or certify compatibility. Documentation review and content hashes are not hardware tests.

## Offline release copy

An offline catalogue asset can be generated for each release: `thinkpad-archive-VERSION-offline.zip` and its `.zip.sha256` checksum. No tagged release includes these assets yet; source availability is separate from downloadable release assets. Once published, download the ZIP from that version's [GitHub release assets](https://github.com/MikelCalvo/thinkpad-archive/releases), extract the entire folder and open `index.html`. No Python, local server, account or installation is needed to browse. English and Spanish are included in one archive.

The archive contains the catalogue, technical profiles and local UI assets, plus the project license, bilingual instructions and source-rights notes. It does not contain manufacturer PDFs, driver installers, private research or live statistics/history. External references and GitHub correction drafts still require Internet. The offline copy never opts into collection; Stats cannot display live counts from a local file.

To generate the same distribution yourself with Python 3.11 or later, from the project directory:

```sh
mkdir -p dist
python3 -m thinkpad_archive offline-release --output dist/offline
```

The output directory must be new. Optionally add `--default-language es` for a Spanish root entry; both languages remain included. The command accepts the same metadata/locale directories as the static builder, but never accepts a prebuilt website or collection opt-in. It verifies the complete ZIP before publishing the two files into the output directory. Existing output is refused unchanged. Ordinary failures clean task-owned partial output; an interruption or power loss can leave incomplete files, so verify the checksum rather than treating directory presence as success.

Each extracted copy includes `SHA256SUMS.json` for its members. The sibling `.zip.sha256` checks the whole ZIP, for example with `sha256sum -c *.zip.sha256` on Linux or `Get-FileHash FILE.zip -Algorithm SHA256` in PowerShell. These hashes detect changed bytes, not publisher identity. Member order, timestamps and modes are fixed; identical compressed bytes are expected only with the same Python/zlib toolchain.

The published-release workflow remains available for manually created releases, including prereleases, and requires a matching `vVERSION` tag at the exact release commit. It builds with read-only permissions and attaches with a separate write-enabled job. Identical existing ZIP/checksum assets are reconciled without another upload; mismatches are refused. The 0.5.3 tag workflow can instead prepare a draft with the files already attached. Neither flow backfills older releases automatically. Check the exact version's workflow run and attached files before relying on a release asset.

## Build locally

You need Python 3.11 or later. The builder uses only the standard library. From the project directory:

```sh
python3 -m unittest discover -s tests -v
mkdir -p build
python3 -m thinkpad_archive build --output build/public
python3 tools/check_site.py build/public
python3 tools/check_seo.py build/public
```

The output destination must not already exist. Open `build/public/index.html` in your browser, including through `file://`. Pages and links work without JavaScript; optional search and filters run on your device. External manual, source and package links still need Internet access. Modern-browser checks do not establish support for every historical browser.

To make Spanish the root language:

```sh
python3 -m thinkpad_archive build --output build/spanish --default-language es
```

The navigation places catalogue/source links on the left and the globe language picker beside the theme and GitHub controls on the right. Subpages use a compact house icon to return home. The neutral entry starts in English by default and remembers an explicit language choice; direct English/Spanish links remain in their requested language. Switching languages keeps the current model, selected year or sources page. Both builds contain metadata and links, not manufacturer documents or installer binaries. The moon/sun control remembers your theme in local browser storage; on a first visit it starts dark, independent of your system preference. A saved light or dark choice takes priority; without scripts the site also starts dark. GitHub and external references open in a new tab, while catalogue navigation stays in the current one.

## Search, shareable navigation and social cards (0.4.4)

Model pages add optional software search and a source-listed operating-system filter. Known OS label spellings are grouped for navigation; each package still displays the original source text, architecture and evidence. An OS filter is not a compatibility certification. Firmware remains separate and is never hidden by software filters. Without scripts, the original complete category lists remain readable.

Catalogue search, family, reference-presence filters and selected year can be shared in the URL. Reload and browser Back/Forward restore that view. Year views retain their clean, filter-free layout; choose ALL to search across the catalogue. These improvements run locally without accounts, network requests or server-side saved searches.

Shared links include static Open Graph and X/Twitter large-card metadata, localized descriptions, page-specific model/year/source titles, canonical URLs and original EN/ES 1200×630 PNG artwork. The metadata uses the official HTTPS domain; local previews let you inspect the files, but social services cannot fetch localhost. The neutral and legacy catalogue entries use the language-specific default catalogue as their canonical URL. Public sharing services can fetch the deployed files, but their cached previews may take time to refresh; local copies cannot be fetched from localhost. Filter query strings retain their interactive behavior but use the page's unfiltered metadata; static crawlers do not execute the local search. No social SDK, account, tracker or automatic post is added. Normal builds copy the checked-in cards without dependencies; `tools/generate_social_cards.py` is an optional artwork-regeneration tool requiring Pillow, rsvg-convert and DejaVu Sans.

## Public statistics (0.5.0)

The footer links to a public EN/ES Stats dashboard. Normal static/offline builds do not collect anything. An explicit opt-in build and same-origin service can keep only public daily marginal page-view counters, without cookies, visitor IDs, raw referrers, raw user agents, IPs or GeoIP. Counts describe views, not unique visitors. Daily counters are retained indefinitely, with an All time period alongside the recent-period filters. The complete stored rows remain publicly accessible through the aggregate API; the dashboard does not include a JSON download block. DNT/GPC suppress collection. See [statistics, privacy limits and optional self-hosted stack](docs/statistics.md).

## CI and release drafts (0.5.3)

CI runs after a branch push or pull request, not when a commit exists only on your computer. It runs the complete tests on Python 3.11 and 3.13 with Node 22 available, checks Python/JavaScript syntax and changed whitespace, builds English-root, Spanish-root and statistics-enabled sites, checks their internal links and packages the offline ZIP. A separate read-only job validates workflow syntax using actionlint 1.7.11. Successful Python 3.13 checks retain the offline files as a short-lived Actions artifact; that is not a published release.

Run the same project checks locally with Python 3.11+ and Node installed:

```sh
mkdir -p build
python3 tools/check.py --output build/checks --package
```

Use a new output path for each run. To validate the workflow files too, use Go 1.24+:

```sh
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.11 -shellcheck= -pyflakes=
```

The first Go invocation downloads the pinned verifier and its dependencies; the catalogue itself has no runtime dependency on Go, Node or actionlint. Shellcheck and pyflakes integrations are explicitly disabled; Python syntax and shipped JavaScript are checked by the project runner.

For a release, update VERSION and its changelog section, review the checks, then explicitly create and push the matching `vX.Y.Z` tag on the intended commit. The tag workflow reruns the same CI before preparing a GitHub DRAFT with the verified ZIP, checksum and changelog notes. It requires an existing matching tag and never creates or moves one. Version 0.x drafts remain prereleases. Review the draft and publish it manually when ready. No workflow deploys the website or changes branch protection; source publication can still trigger the existing separate Coolify webhook described in the deployment guide.

Draft creation attaches its assets in the same run: events created with the default GITHUB_TOKEN do not reliably start a second workflow, so the release flow does not depend on the published-release hook. The older published-release workflow remains a fallback for manually created releases. If both expected assets already exist with identical GitHub-reported SHA-256, size and uploaded state, it does nothing; missing/changed/partial asset sets are refused rather than overwritten. A failed or ambiguous create/upload requires inspecting the existing release before retrying. Network/authentication errors never become permission to create a duplicate.

The 0.5.3 source passed 307 local tests on each of Python 3.11 and 3.13, plus fresh builds, internal-link checks, offline packaging and workflow validation. Hosted status is reported in [GitHub Actions](https://github.com/MikelCalvo/thinkpad-archive/actions); local checks are not a hosted result. Real tag-driven draft creation and attachment remain unverified until that release flow is exercised. Checks can be made required through repository rules later, but no such settings are changed by these files. CI does not certify external download availability, historical-browser support or hardware compatibility.

## Search-engine discovery (0.5.4)

Fresh builds include `robots.txt` and `sitemap.xml`. The sitemap lists official HTTPS canonical EN/ES model, catalogue, source and populated-year pages, without aliases, query filters, statistics or empty/unconfirmed-year navigation. Hreflang sets are absolute, reciprocal and self-inclusive, with the selected default language as x-default. Native navigation stays relative and works offline. Statistics and empty/unconfirmed-year pages remain accessible but carry `noindex,follow`; duplicate catalogue entries use canonical preferences instead of noindex.

Static titles/descriptions and escaped Schema.org WebSite/page data describe the actual archive, not a shop or an official IBM/Lenovo publication. The inert JSON-LD has a page-specific CSP hash; no executable inline permission, tracking library, invented dates, offers, reviews or ratings are added. Search engines may choose different titles or canonical URLs. The shared check runner now validates generated SEO files and metadata as well as links. See [indexing checks and webmaster setup](docs/seo.md).

Source publication, production deployment, search-engine ownership verification and sitemap submission are separate steps. Local validation alone establishes none of them. Crawlability helps discovery but does not guarantee crawling, inclusion, rich results or ranking. Metadata uses the official production origin; keep previews loopback-only or independently access-controlled rather than exposing a second public mirror.

## Hosting

The public site is at **[thinkpadarchive.com](https://thinkpadarchive.com/)**. You can host the generated files on a static web server, or use the included Docker setup. See the [deployment guide](docs/deployment.md) for container hosting and Coolify configuration.

## Contributing

Model pages include a Suggest a correction / Proponer una corrección link below each overview. It opens a GitHub issue draft with the exact model name, catalogue ID and public page URL, plus prompts for the proposed correction and sources. Review the draft and submit it yourself; sending requires a GitHub account. The link also works without JavaScript and from a local copy, but GitHub needs Internet access. Only public catalogue fields are prefilled, never local file paths, browser preferences or visit data. Do not include serial numbers or personal information.

Corrections, source links and translations are welcome. Please include the exact model or machine-type qualifier and the source URL; prefer primary manufacturer sources. Keep grouped source identities intact unless a reliable source establishes an individual variant. Do not assign packages by family-name resemblance.

For a new language, add a complete locale JSON with the same keys as the existing languages. Translate project interface text and warnings, while preserving original product titles and operating-system identifiers. Do not redistribute or translate a manufacturer document as part of this project.

Before proposing a release, run the tests and link checker, inspect both languages and narrow layouts, and review the [release checklist](docs/release-checklist.md).

## License and source rights

Original project code, documentation, tests, translations and artwork are available under the [MIT License](LICENSE), copyright 2026 MikelCalvo.

The catalogue publishes factual metadata and source links. It does not mirror manufacturer PDFs, driver binaries, original README bodies or captured websites, and it contains no personal inventory or local-device records. The project license does not grant rights to third-party documents, software, websites or trademarks. Public availability and content hashes are not redistribution permission.

See [sources, attribution and publication boundary](docs/sources-and-rights.md) for the full distinction. ThinkPad, IBM, Lenovo and other product names belong to their respective owners.
