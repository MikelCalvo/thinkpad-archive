# Public statistics and privacy

Statistics are an explicit opt-in hosting mode. Normal static and offline builds do not collect anything. Enabling this service is a separate deployment choice; upgrades do not silently turn it on.

## What is counted

With JavaScript enabled and accepted, one ordinary document load can add one JavaScript page view. Search/filter changes and the Stats dashboard do not add views. Counts are not unique visitors, sessions or durations. Blocking, DNT, GPC, bots and spoofed browser/referrer categories affect coverage and accuracy.

The optional collector runs on the same origin. It reduces a referrer to direct, internal, search, GitHub, Reddit, Hacker News, social or other before sending. Unknown domains become other, not a stored hostname. It reduces the user agent in memory to coarse device, browser and operating-system categories. Only the generated document pathname and those four finite categories are submitted. Query strings, fragments, raw referrers and raw user agents are not submitted. No cookies, analytics IDs, local storage, fingerprinting, IP hashes or cross-page visitor linkage are used. Country and GeoIP are deliberately absent; no geographic provider or downloaded geographic database is needed.

The existing theme and language controls use local browser preferences, independently of analytics; those preferences are not submitted to the analytics service.

From 0.5.6, the opt-in stack also counts full catalogue ZIP responses successfully written by its own service. This is not a click event, a unique-person count, proof that a browser saved/extracted the file, or a hardware acknowledgement of receipt. The public dashboard shows Catalogue downloads / Descargas del catálogo separately from page views, using the same period selector. Only collection from activation onward is included; no earlier downloads are inferred. HEAD, Range requests, checksums, other files, invalid/query-bearing paths, failed sends and DNT/GPC opt-outs do not increment it. A disconnect detected during sending omits the count; disconnects after bytes enter network/proxy buffers may not be detected. A failed counter write after delivery also omits the count and is not retried. Bots and repeated downloads can increase it. Static-only hosting, offline files and GitHub release assets do not report transfers to this counter.

## HTML document traffic: a separate population

From 0.5.6 the opt-in proxy delivers an exact generated-document allowlist through the first-party backend. A successful full HTML GET can add one `document-traffic` daily marginal even when the client never executes JavaScript. This does not increment JavaScript page views or ZIP downloads. Do not add the populations together, infer unique people, or compare their difference as a bot count. Older stored views remain unclassified; no historical browser traffic is backfilled.

Transient User-Agent text (maximum 2048 ASCII characters) reduces to one of `browser`, `unknown`, `other-bot`, Googlebot, Bingbot, DuckDuckBot, Baiduspider, YandexBot, Applebot, GPTBot, OAI-SearchBot, ClaudeBot, Bytespider, PetalBot or Amazonbot. Token matching is case-insensitive with explicit product/version boundaries; hostile prefixes, suffixes and URL/domain occurrences do not establish a named crawler. Other declared bots, crawlers, spiders, headless clients and common automation tools use `other-bot`. Missing, duplicate, oversized or unrecognized UA fields use `unknown`. **Browser-like is not verified human traffic; names are spoofable declarations, not verified crawler identities.** There is no IP, DNS, reverse-DNS or GeoIP verification, enrichment or raw-UA storage.

DNT/GPC exclude collection, including duplicate and whitespace-padded opt-out fields. HEAD, Range, errors, dashboard HTML, APIs, downloads and assets do not count as documents. Query strings are ignored for route selection and never retained. Only a successful full server write counts, not proof of reception: socket/proxy buffers may outlive disconnects; interrupted sends or failed counter writes can omit counts. The EN/ES dashboard shows a labelled comparison, exact native counts, declared crawler breakdown and full daily table on the same period/refresh as existing metrics. Zero, unavailable and older-API absence are distinct.

## The entire analytics database is public data

SQLite contains only:

    counts(day, dimension, value, count)
    PRIMARY KEY(day, dimension, value)

An accepted view increments seven separate daily marginals: total, page, source, device, browser, system and language. It does not retain the combination as an event or visitor record. Downloads add only a `download` dimension whose value is the generated numeric `major.minor.patch` version, with a UTC day and count. No source, language, device, browser or system categories are attached to downloads. HTML traffic adds only the finite `document-traffic` dimension, without a page, source, language, device, browser or system join. Its browser-like/bot/unknown totals, crawler breakdown and daily series are derived from that single marginal. This uses the unchanged table schema and preserves every existing row; view totals never include download counts. A page cannot be filtered by its visitors' device/source. All stored rows and fields, not only the dashboard's selected period, are available without login at /api/stats/export.json. SQLite journals contain the same aggregate data, not raw events. Counters are retained indefinitely as part of the archive. Startup, reads, writes and period changes never delete historical counts. Repeated exports can expose changes in low-volume counters; aggregation is not differential privacy.

The application writes no access/request logs. The optional bundled Caddy configuration discards its own request/error logs, but an outer HTTPS proxy, host, backups or monitoring system may have separate logs. Inspect that infrastructure before making a site-wide no-IP-storage claim. Network peers necessarily see a connecting address transiently; this application does not store or enrich it.

## Build and run locally

The default build remains static/offline-readable and has no collector:

    mkdir -p build
    python3 -m thinkpad_archive build --output build/static
    python3 tools/check_site.py build/static

For an explicit local collection preview (use fresh output names):

    mkdir -p build
    python3 -m thinkpad_archive build --output build/stats --enable-stats
    python3 tools/check_site.py build/stats --allow-stats-api
    install -d -m 0700 build/stats-data
    python3 -m thinkpad_archive.stats_server --site-root build/stats --database build/stats-data/counts.sqlite --origin http://127.0.0.1:8080 --listen 127.0.0.1 --port 8081 --enabled

The backend is not a general static file server: it delivers only its fixed generated HTML and ZIP snapshots. Put a same-origin proxy in front: serve build/stats at http://127.0.0.1:8080 and proxy the exact generated documents, /api/stats/* and exact /downloads/thinkpad-archive-MAJOR.MINOR.PATCH-offline.zip paths to 127.0.0.1:8081. Dashboard, checksum files and other resources remain static. Use deploy/Caddyfile.stats and generate its required matcher **outside the public directory**:

    python3 -c "from thinkpad_archive.stats_server import document_proxy_matcher; from pathlib import Path; Path('build/document-routes.caddy').write_text(document_proxy_matcher('build/stats'))"

For local use, adapt the Caddy root/upstream and the absolute import `/etc/caddy/document-routes.caddy` to that generated file. The Docker `stats-build` target generates it automatically; `stats-web` copies it outside `/srv`. The matcher is an exact path list, not an HTML wildcard: `/`, `/index.html`, locale directory defaults, index/catalogue legacy entries, models, years and sources only. The backend independently snapshots the same route set; no client path becomes a filesystem read. It rejects symbolic/hard links, nonregular, oversized and identity-changed files. HTML bytes are cached compressed at startup (2 MiB per file, 256 MiB source snapshot, 32 MiB compressed-cache cap, at most 10000 routes), retaining the existing 128 MiB container limit; restart with a coherent rebuilt root after changes. The database must be outside the public directory, owned by the service UID with a private 0700 parent. No symlinks are accepted. Listen addresses are numeric IPv4; IPv6 is not implemented. The exact configured Origin has no trailing slash and must match the browser's origin, not the internal backend address. Origin checking reduces accidental cross-site submissions; it does not authenticate humans or prevent deliberate counter spoofing.

## Optional Docker stack

The last/default Docker target remains static. The opt-in stack uses separate stats-build, stats and stats-web targets, with a persistent private counts volume and no publicly exposed API container port:

    ANALYTICS_ORIGIN=http://127.0.0.1:8080 docker compose -f deploy/compose.stats.yaml up --build -d

Open http://127.0.0.1:8080/es/stats.html. By default the web listener binds host loopback. Explicitly configure STATS_BIND, STATS_PORT and ANALYTICS_ORIGIN for a different authorized deployment. No production rollout is implied by these commands. Set the existing private COOLIFY_WEBHOOK_UPSTREAM only if that deployment uses its existing authenticated webhook path; the stats stack does not create a webhook or store its secret.

The volume initializer only sets owner 10001:10001 and mode 0700 on /data. The service and Caddy then run unprivileged, read-only, with dropped capabilities. The backend has a private internal Docker network; only web joins the egress network. Caddy strips Cookie, Authorization, Referer and forwarding/IP headers on document, API and ZIP proxy branches. User-Agent is forwarded **only** on the document branch for transient classification; it is stripped on API/ZIP branches. DNT, Sec-GPC and Origin remain. No raw requests are logged. Both containers disable Docker logs. Global process limits, not IP-based limits: eight workers and a shared token bucket of 240 requests with refill 60/second. API and HTML requests and slow headers retain their two-second absolute deadline; HTML delivery never receives the ZIP allowance. Only an admitted ZIP send receives a separate 30-second absolute transfer deadline, still under the same worker/rate caps; archive files are capped at 512 MiB. An upstream deployment may need additional global abuse controls. These measures cannot certify counters as human visits.

To stop the optional stack without deleting aggregate data:

    docker compose -f deploy/compose.stats.yaml down

Do not add --volumes unless deleting the stored aggregate history is intended. Preserve the volume during upgrades; a static-only rollback can leave it untouched.

## Public API

- POST /api/stats/pageview: exact JSON string fields path, source, device, browser, system; generated routes only, 1024-byte maximum, exact same Origin. Accepted or DNT/GPC-opted-out requests return 204. The dashboard, arbitrary routes, query strings, fragments, extra fields and arbitrary categories are refused.
- GET /api/stats/data?days=30: allowed windows 7, 30, 90, 365 and all (All time / Todo el tiempo). The all-time window starts at the earliest stored UTC day and includes zero-filled days through today; an empty archive starts at today. Period filters only affect the response, never storage. Metadata uses retention_days: null to mean indefinite retention.
- GET /api/stats/data also returns `documents: {total, browser, bots, unknown, crawlers, daily}` for the same window. Daily entries contain `{day, total, browser, bots, unknown}`; crawlers are finite `{value, count}` entries, sorted by count descending then name. These are document requests, not the JavaScript `total`. Older API absence displays a dash and explicit notice, never fabricated zero or historic classification.
- GET /api/stats/data also returns `downloads: {total, daily, versions}` for the same window, without changing the page-view `total` or marginals. An older API without this field displays an unavailable dash, not an invented download zero.
- GET /downloads/thinkpad-archive-MAJOR.MINOR.PATCH-offline.zip: only files snapshotted from the generated downloads directory, with size/identity checks. Full successful sends increment only the download aggregate. HEAD returns metadata without counting; Range returns 416 without counting. There is no client-submitted download-event endpoint.
- GET /api/stats/export.json: privacy metadata and every retained {day, dimension, value, count} row, including download and document-traffic rows.
- GET /api/stats/health: readiness, no collection.

Responses have no-store and nosniff; no cookies or wildcard CORS. API GET/HEAD/OPTIONS never create JavaScript views. Only admitted full document GETs create document traffic. Disabled API mode creates no database and reports disabled zero data; health/ingestion are unavailable. A file:// dashboard shows an explicit unavailable state and does not contact an API. Without JavaScript the methodology remains readable. The dashboard has no complete-JSON download section; public aggregate API access remains available for transparency.

## Verification

Run the repository suite with python3 -m unittest discover -s tests -v. Frontend behavioral tests also require Node.js; the app itself has no Node runtime dependency. Integration checks must exercise a real same-origin proxy, empty and nonempty live data, public-export versus SQL equality, history older than a year, all-time windows, reopen/persistence, opt-outs, no-query/fragment collection, responsive EN/ES UI, file:// and no-script behavior. Test traffic is not real visitor traffic and must use an isolated database, never seed public numbers.
