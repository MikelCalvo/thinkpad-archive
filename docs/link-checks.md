# External-link availability

## Dated result

Checked on 29 October 2026, **20:27:57–20:46:49 UTC**, against the five catalogue JSON files. The audit covered **5,493 unique URLs and all 64,319 source-field references**, deduplicating only URL fragments. There were no unchecked targets.

| Result | Unique URLs |
| --- | ---: |
| Responded to HEAD with HTTP 200 | 5,460 |
| HTTP 404 confirmed by HEAD and bounded GET | 31 |
| HTTP 403 with a challenge marker | 1 |
| HTTP 429 rate limit | 1 |
| Not checked | 0 |

The [machine-readable report](audits/external-links-2026-10-29.json) includes source-input and tool hashes, exact source JSON pointers for every non-positive result, the five redirect chains, limits and timestamps. Positive results are summarized, not listed as individually verified documents. The retained raw metadata checkpoint has a SHA-256 in that report; no response bodies are published.

Five URLs redirected, and their final endpoints responded with HTTP 200. One Forbes URL led to a consent page, not the article itself. The other observed redirects added a trailing slash or a `www` hostname. **HTTP 200 proves only that an endpoint responded at that time.** It does not prove the requested document is present, detect every soft-error/login/consent page, establish file identity or certify compatibility. All 5,460 positive results were HEAD-only: their response bodies were deliberately not downloaded.

The challenge was [Tweakers' X200si listing](https://tweakers.net/pricewatch/256747/lenovo-thinkpad-x200si-ns2fvmh.html); the rate limit was [VentureBeat's ThinkPad announcement](https://venturebeat.com/ai/lenovo-updates-thinkpad-lineup-with-intel-8th-gen-processors-and-usb-type-c-power-adapters). Each appears in two source fields. Neither result is classified as a missing link, and no access control was bypassed.

## Confirmed missing at the time of the audit

These **31 destinations affect 138 source-field references**: 30 are hosted by Lenovo and one by Macdat. Each returned HTTP 404 for HEAD and for a separate, size-capped GET. The counts below are references, not distinct machines or packages.

| Original destination | References |
| --- | ---: |
| [1ety48ww.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/1ety48ww.txt) | 1 |
| [1khj06jp.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/1khj06jp.exe) | 1 |
| [1khj06jp.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/1khj06jp.txt) | 1 |
| [tp_x230x_tablet_w732_201308.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w732_201308.exe) | 1 |
| [tp_x230x_tablet_w732_201308.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w732_201308.txt) | 1 |
| [tp_x230x_tablet_w764_201308.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w764_201308.exe) | 1 |
| [tp_x230x_tablet_w764_201308.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w764_201308.txt) | 1 |
| [tp_x230x_tablet_w832_201210.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w832_201210.exe) | 1 |
| [tp_x230x_tablet_w832_201210.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w832_201210.txt) | 1 |
| [tp_x230x_tablet_w864_201210.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w864_201210.exe) | 1 |
| [tp_x230x_tablet_w864_201210.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles/tp_x230x_tablet_w864_201210.txt) | 1 |
| [240ucdrw.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles_pdf/240ucdrw.exe) | 2 |
| [240ucdrw.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles_pdf/240ucdrw.txt) | 2 |
| [240xcdrw.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/mobiles_pdf/240xcdrw.exe) | 2 |
| [1v29ez00lmc-c.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/thinkcentre_drivers/1v29ez00lmc-c.exe) | 8 |
| [1v29ez00lmc-c.txt](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/thinkcentre_drivers/1v29ez00lmc-c.txt) | 8 |
| [systemupdate3.16-2013-7-10.exe](https://download.lenovo.com/ibmdl/pub/pc/pccbbs/thinkvantage_en/systemupdate3.16-2013-7-10.exe) | 68 |
| [SL500.html](https://download.lenovo.com/lenovo/content/ddfm/SL500.html) | 1 |
| [sif10ww760.exe](https://download.lenovo.com/pccbbs/mobiles/sif10ww760.exe) | 3 |
| [sif10ww760.txt](https://download.lenovo.com/pccbbs/mobiles/sif10ww760.txt) | 3 |
| [02r2914.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/02r2914.pdf) | 1 |
| [13n6183.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/13n6183.pdf) | 1 |
| [23p0894.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/23p0894.pdf) | 1 |
| [24p2911.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/24p2911.pdf) | 1 |
| [24p2914.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/24p2914.pdf) | 1 |
| [39t2462_01.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/39t2462_01.pdf) | 1 |
| [39t9290.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/39t9290.pdf) | 1 |
| [42t7844_04.pdf](https://download.lenovo.com/pccbbs/mobiles_pdf/42t7844_04.pdf) | 1 |
| [systemupdate5.07.0053.exe](https://download.lenovo.com/pccbbs/thinkvantage_en/systemupdate5.07.0053.exe) | 10 |
| [systemupdate5.07.0053.txt](https://download.lenovo.com/pccbbs/thinkvantage_en/systemupdate5.07.0053.txt) | 10 |
| [330.php](https://macdat.net/laptops/ibm/thinkpad/330.php) | 2 |

These historical URLs remain in the catalogue as provenance. This release documents their observed unavailability instead of inventing replacements, removing source evidence or silently changing package/model associations. A 404 is not a permanent claim about a host. Corrections need an exact matching primary source or a clearly attributed archival alternative, including the model/package identity and source date; a similarly named file is insufficient. See [safe contributions](catalogue.md#safe-contributions).

## Tool provenance and safety correction

The dated observations were produced by the original audit tool with SHA-256 `757d32aaba08d18d47678094ebe24e08b0ff8d2fc792f1e0e327d1b8e8f2ba76`, recorded as `tool_sha256` in the report. Pre-release review found that Python's `is_global` address property alone also accepts multicast. The shipped tool now explicitly rejects multicast in both literal URLs and every DNS answer, including redirects. Offline IPv4/IPv6, mixed-answer and socket-admission regressions cover that correction. The saved audit remains attributed to its original tool; it was not rerun or relabelled as an execution of the hardened successor. No incorrect HTTP observation was established by this finding.

## Reproduce the audit

From a Git checkout, choose a new evidence directory:

```sh
mkdir -p build
python3 tools/check_external_links.py \
  --source . --output build/link-audit-2026-10-29 \
  --workers 8 --timeout 12 --max-duration 2650
```

This command explicitly contacts external hosts. It inventories tracked `data/*.json` files, hashes their actual working bytes, writes source bindings before starting network requests, checkpoints each result and reconciles the complete URL set at the end. Existing output is refused; resume is not supported. A later run observes a different moment and may have different results even with identical inputs.

The tool uses eight global workers, at most four active exchanges per hostname and a minimum 75 ms between request starts for the same hostname. It validates public destinations at every redirect, pins the resolved IP, verifies TLS, and sends no cookies or credentials. DNS, TLS, headers and prefix reading share a whole-exchange subprocess deadline of 12 seconds. Redirects are limited to five per URL. Inconclusive HEAD statuses can trigger one bounded GET chain with `Range: bytes=0-1023`; the application reads at most 1,024 bytes even if the server ignores Range. HEAD 404/410 is not confirmed missing without GET confirmation.

This run made 5,531 HTTP exchanges and read 33,219 bytes of prefixes, at most 1,024 per URL. No PDFs or installers were downloaded in full and no bodies were retained. Prefix bytes are application-delivered bytes, not total network/TLS/header traffic. The configured aggregate network deadline was 2,650 seconds; it completed in 1,132 seconds. Final metadata reconciliation/checkpoint work is separate from that network budget.

Exit 0 means every target received a result, **not that every link works**. Exit 2 means targets remained unrequested at the cutoff. Inspect `summary.json`, `results.jsonl` and the inventory, not just the exit code. Blocked/challenged, rate-limited, server, DNS/TLS/transport, timeout and missing results stay separate. Offline tests cover classification, bounds, public-destination checks and checkpoints; mandatory CI does not run a live crawl.

## Scope of the stable release

The audit does not change catalogue facts, remove unavailable historical references, mirror manufacturer materials or claim permanent external availability. Follow the exact package README and machine/OS requirements before installing anything. See [sources and rights](sources-and-rights.md) and [known data gaps](data-quality.md).
