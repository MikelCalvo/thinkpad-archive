/* Optional first-party document counter. No state, IDs or lifecycle tracking. */
(function () {
  "use strict";
  try {
    if (document.documentElement.getAttribute("data-stats-enabled") !== "true" ||
        (location.protocol !== "https:" && location.protocol !== "http:")) { return; }
    function optedOut(value) { return value === "1" || value === 1 || value === "yes"; }
    if (navigator.globalPrivacyControl === true || optedOut(navigator.doNotTrack) ||
        optedOut(navigator.msDoNotTrack) || optedOut(window.doNotTrack)) { return; }
    var path = location.pathname;
    // Only document-shaped public paths; the server checks generated-route membership.
    if (typeof path !== "string" || path.length > 512 ||
        !/^\/(?:[a-zA-Z0-9_-]+\/)*(?:[a-zA-Z0-9_-]+\.html)?$/.test(path) ||
        /(?:^|\/)stats\.html$/.test(path)) { return; }

    function matches(host, domain) {
      return host === domain || host.endsWith("." + domain);
    }
    function oneOf(host, domains) {
      return domains.some(function (domain) { return matches(host, domain); });
    }
    function source() {
      if (!document.referrer) { return "direct"; }
      try {
        var ref = new URL(document.referrer);
        if (ref.protocol !== "https:" && ref.protocol !== "http:") { return "other"; }
        if (ref.origin === location.origin) { return "internal"; }
        var host = ref.hostname.toLowerCase();
        if (matches(host, "github.com")) { return "github"; }
        if (matches(host, "reddit.com")) { return "reddit"; }
        if (host === "news.ycombinator.com") { return "hacker-news"; }
        if (oneOf(host, ["google.com", "google.es", "google.co.uk", "google.de", "google.fr", "google.it", "google.pt", "google.ca", "google.com.au", "bing.com", "duckduckgo.com", "search.yahoo.com", "search.brave.com", "ecosia.org", "startpage.com", "qwant.com"])) { return "search"; }
        if (oneOf(host, ["x.com", "twitter.com", "t.co", "facebook.com", "instagram.com", "linkedin.com", "threads.net", "bsky.app", "mastodon.social", "t.me"])) { return "social"; }
      } catch (_) { /* Invalid referrers are not transmitted. */ }
      return "other";
    }
    var ua = typeof navigator.userAgent === "string" ? navigator.userAgent.toLowerCase() : "";
    var system = !ua ? "unknown" : /android/.test(ua) ? "android" : /iphone|ipad|ipod/.test(ua) ? "ios" :
      /windows/.test(ua) ? "windows" : /macintosh|mac os x/.test(ua) ? "macos" : /linux|x11/.test(ua) ? "linux" : "other";
    var device = !ua ? "unknown" : /ipad|tablet|kindle|silk/.test(ua) || (system === "android" && !/mobile/.test(ua)) ? "tablet" :
      /mobile|iphone|ipod/.test(ua) ? "mobile" : system !== "other" ? "desktop" : "unknown";
    var browser = !ua ? "unknown" : /edg(?:e|a|ios)?\//.test(ua) ? "edge" : /opr\/|opera|opios\//.test(ua) ? "opera" :
      /firefox\/|fxios\//.test(ua) ? "firefox" : /chrome\/|crios\/|chromium\//.test(ua) ? "chrome" :
      /safari\//.test(ua) ? "safari" : "other";
    fetch("/api/stats/pageview", {
      method: "POST", mode: "same-origin", credentials: "omit", referrerPolicy: "no-referrer",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({path: path, source: source(), device: device, browser: browser, system: system})
    }).catch(function () { /* Optional collection must not disrupt browsing. No retries. */ });
  } catch (_) { /* Disabled browser APIs are a quiet no-op. */ }
}());
