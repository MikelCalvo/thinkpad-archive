# Search discovery and indexing

Version 0.5.4 includes technical SEO improvements. Its presence in the source repository does not establish that the public site has deployed it or that a search engine has indexed it. Technical correctness makes discovery easier; crawling, canonical selection, inclusion, rich results and ranking are search-engine decisions.

## What the build emits

- `robots.txt` permits catalogue pages and local resources, advertises `https://thinkpadarchive.com/sitemap.xml` and discourages crawling operational `/api/`, `/_deploy/` and `/healthz` routes. It is not access control, authentication or a guaranteed URL-removal mechanism.
- `sitemap.xml` contains only official HTTPS canonical language-root catalogues, source pages, exact model routes and years with recorded model entries. It excludes neutral/index/catalogue aliases, query filters, statistics, empty-year pages, unconfirmed-year navigation, external documents and assets. It has no generated `lastmod`, `priority` or `changefreq` claims.
- Static canonical links preserve each page's language. English and Spanish counterparts have reciprocal, self-inclusive absolute hreflang sets; x-default points to the configured default language's matching page. This does not replace the relative body links or offline language preference target.
- Neutral and legacy catalogue entries retain canonical preferences, not blanket noindex. Statistics and empty/unconfirmed-year navigation remain readable but use `noindex,follow`; they are not disallowed in robots, so compliant crawlers can read that instruction.
- HTML titles match Open Graph titles. Model names and qualifiers remain exact; descriptions are localized. The statistics page has its own description rather than describing the catalogue.
- A single escaped JSON-LD graph identifies WebSite and the actual WebPage or CollectionPage, its language and canonical URL. Model pages may name their visible subject as a Thing, not a commercial product offer. No unsupported dates, ratings, reviews, prices, false affiliation, fake breadcrumbs or retired search-box markup are added. The exact inert script bytes are bound by a CSP SHA-256 source without allowing arbitrary inline scripts.

All data and UI content remains static and browser-readable without JavaScript. Public metadata uses the official origin, including in an offline ZIP; this metadata does not trigger network fetches. Native assets and navigation remain local. Keep previews loopback-only, authenticated or separately marked nonindexable at the hosting boundary; a canonical hint is not protection against public preview indexing.

## Local verification

Run the complete test/build/link/SEO/package path with Python 3.11+ and Node installed, choosing a new output directory:

```sh
mkdir -p build
python3 tools/check.py --output build/checks --package
```

To inspect a fresh existing build alone:

```sh
python3 tools/check_site.py build/checks/english
python3 tools/check_seo.py build/checks/english
```

The SEO checker reads actual generated HTML and XML without fetching external URLs. It validates canonical and alternate existence/locality, reciprocal sets, sitemap membership, robots guidance, unique metadata and JSON-LD/CSP consistency. It is not a substitute for a search engine's live URL inspection, real-browser checks, external download verification or hardware compatibility testing.

## After an authorized production deployment

1. Verify the deployed commit separately from the GitHub source commit. Fetch the real robots.txt and sitemap.xml with a fresh request. Require HTTP 200, correct UTF-8/plain-text or XML content and URLs on the official HTTPS domain. A local passing checker or an old public page is not deployment evidence.
2. Check the English/Spanish catalogue, a model, Sources, a populated year and Stats. Ensure the public response has no accidental global noindex or X-Robots-Tag block, canonical/alternate targets exist, CSS/JS can be crawled and missing pages return real 404 rather than an indexable soft-404 shell. Confirm HTTP/HTTPS and any hostname redirects through the actual edge; this candidate does not change DNS or the reverse proxy.
3. For Google, sign in to [Search Console](https://search.google.com/search-console/), add the appropriate property and complete the ownership method supplied by Google. A domain property uses DNS verification; a URL-prefix property may offer other methods. DNS/account/file changes require explicit operator approval, and verification values must not be guessed or posted in chat.
4. In the verified property's Sitemaps report, submit `https://thinkpadarchive.com/sitemap.xml`. Inspect representative model and language URLs with the live URL-inspection tool. Google documents that a successful sitemap fetch does not mean every listed URL will be crawled or indexed.
5. For Bing, sign in to [Bing Webmaster Tools](https://www.bing.com/webmasters/), add and verify the site using the offered method, or explicitly approve importing an already-verified Search Console property. Submit the same official sitemap in the Sitemaps section. Review processing and URL-inspection reports separately from submission success.
6. Record the actual submission date and reports; monitor indexing errors and impressions over time rather than claiming an immediate ranking change. This code does not create accounts, import properties, submit URLs, add IndexNow keys, run paid promotion or install analytics/trackers. Other crawlers can discover ordinary links and the standards-based sitemap, but support and inclusion vary.

Do not add hundreds of near-identical keyword pages or promise universal indexation. The useful work remains accurate model content, source-backed links, a discoverable site, stable URLs and reasonable page performance. Public archive page-view totals are not search impressions or ranking measurements.

## Primary references

- [Google: building and submitting sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google: localized page versions and hreflang](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google: canonical URL signals](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google: site names](https://developers.google.com/search/docs/appearance/site-names)
- [Google: structured-data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
- [Google: robots.txt limitations](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Search Console: Sitemaps report](https://support.google.com/webmasters/answer/7451001)
- [Bing: getting-started checklist and sitemap submission](https://bing.com/webmaster/help/getting-started-checklist-66a806de)
