# Development

## Requirements

- Python 3.11 or later for the builder and Python tests. The application uses the standard library.
- Node.js for JavaScript syntax and behavior checks. Node is a development dependency, not a catalogue runtime.
- Docker with BuildKit for container builds. Go 1.24 or later is needed only when running the pinned workflow verifier below.

## Run the checks

From a fresh checkout, with Python and Node available:

```sh
mkdir -p build
python3 tools/check.py --output build/checks --package
```

Choose a new output path for every run. The command runs the complete test suite, Python and JavaScript syntax checks, fresh English-root, Spanish-root and statistics-enabled builds, internal links, SEO checks and offline packaging. It fails if a child check fails. These checks do not fetch the catalogue's external links.

To run only the Python-selected suite:

```sh
python3 -m unittest discover -s tests -v
```

JavaScript behavioral cases skip when Node is absent. For release acceptance use the complete check command with Node present, so those cases actually run.

To validate the GitHub Actions files:

```sh
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.11 -shellcheck= -pyflakes=
```

The first invocation downloads the pinned verifier and its dependencies. Shellcheck and pyflakes integrations are disabled; the shared check runner handles Python syntax and shipped JavaScript.

## Audit catalogue metadata

```sh
python3 tools/catalogue_audit.py
```

The audit reads validated public metadata and reports deduplicated source, model and package counts. It does not fetch URLs or execute source material. Optional selector reconciliation reads an explicitly supplied local JavaScript file as text, never evaluates it.

The separate [external-link audit](link-checks.md) performs bounded, explicit network checks. Live availability is deliberately outside the deterministic offline CI gate: a vendor outage, rate limit or bot challenge must not become a fabricated catalogue failure.

## Repository layout

| Path | Purpose |
| --- | --- |
| `data/` | Public factual metadata and source URLs |
| `locales/` | Project-authored English and Spanish interface text |
| `assets/` | Local styles, scripts and original artwork |
| `thinkpad_archive/` | Validation, rendering, offline packaging and optional statistics |
| `tools/` | Audits, verification and release helpers |
| `tests/` | Synthetic fixtures and automated regressions |
| `deploy/` | Caddy and optional Docker Compose configuration |
| `docs/` | Usage, evidence, operations and maintenance guides |

Keep research captures, manufacturer PDFs/installers, credentials, personal inventories and live databases outside the repository. A file removed from the current tree can still exist in Git history; check the publication boundary before pushing.

## CI and validation boundaries

Branch pushes and pull requests run the shared checks on Python 3.11 and 3.13 with Node 22. A separate job validates workflow syntax. Python 3.13 retains the verified offline files as an Actions artifact. Check the exact commit's [Actions run](https://github.com/MikelCalvo/thinkpad-archive/actions); a local success or another commit's green run is not its hosted result.

The 0.5.6 baseline passed 358 tests on each supported Python version, both final Docker targets, isolated proxy/SQLite checks and Chromium flows including keyboard, narrow layouts, no-script and extracted-file use. Its source, tag and published-asset workflows also completed successfully. This is baseline evidence, not a claim that every later change has passed or that Firefox, historical browsers and physical hardware were certified.

Use the [release checklist](release-checklist.md) for the current candidate. Record real failures and unresolved limitations; do not weaken checks or invent missing evidence to declare a version complete.
