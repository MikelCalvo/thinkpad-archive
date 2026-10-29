/* Read-only public dashboard: no collector, cookies, identifiers or storage. */
(function () {
  "use strict";
  var root = document.getElementById("stats-dashboard");
  if (!root) { return; }
  function element(name) { return document.getElementById("stats-" + name); }
  var copy;
  try { copy = JSON.parse(root.getAttribute("data-stats-copy")); } catch (_) { return; }
  var status = element("status"), results = element("results"), selector = element("days");
  function unavailable(key) {
    results.hidden = true;
    element("total").textContent = "—";
    element("download-total").textContent = "—";
    element("window").textContent = "—";
    status.textContent = copy[key];
  }
  if (location.protocol !== "https:" && location.protocol !== "http:") {
    unavailable("file");
    return;
  }
  var windows = [7, 30, 90, 365, "all"];
  var dimensions = {
    sources: ["direct", "internal", "search", "github", "reddit", "hacker-news", "social", "other"],
    devices: ["desktop", "mobile", "tablet", "unknown"],
    browsers: ["firefox", "chrome", "safari", "edge", "opera", "other", "unknown"],
    systems: ["windows", "macos", "linux", "android", "ios", "other", "unknown"],
    languages: null, pages: null
  };
  var prefixes = {sources: "source_", devices: "device_", browsers: "browser_", systems: "system_", languages: "language_"};
  function integer(value) { return Number.isSafeInteger(value) && value >= 0; }
  function language(value) { return typeof value === "string" && /^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/.test(value); }
  function page(value) {
    return typeof value === "string" && value.length <= 512 &&
      /^\/[a-z]{2,3}(?:-[a-z0-9]{2,8})*\/(?:[a-zA-Z0-9_-]+\/)*(?:[a-zA-Z0-9_-]+\.html)?$/.test(value) &&
      !/(?:^|\/)stats\.html$/.test(value);
  }
  function utcDay(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) { return NaN; }
    var stamp = Date.parse(value + "T00:00:00Z");
    return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0, 10) === value ? stamp : NaN;
  }
  function valid(data, days) {
    if (!data || data.enabled !== true || !integer(data.total) || !data.window ||
        data.window.days !== days || data.export_url !== "/api/stats/export.json") { return false; }
    var privacy = data.privacy;
    if (!privacy || privacy.storage !== "daily_marginal_counters" || privacy.retention_days !== null ||
        privacy.timezone !== "UTC" || privacy.unique_visitors !== false || privacy.no_cookies !== true ||
        privacy.no_identifiers !== true || privacy.geo !== false) { return false; }
    var from = utcDay(data.window.from), to = utcDay(data.window.to);
    var length = (to - from) / 86400000 + 1;
    if (!Number.isFinite(from) || !Number.isFinite(to) || !Number.isSafeInteger(length) || length < 1 ||
        (days !== 'all' && length !== days) ||
        !Array.isArray(data.daily) || data.daily.length !== length) { return false; }
    var total = 0;
    for (var d = 0; d < length; d += 1) {
      var day = data.daily[d];
      if (!day || utcDay(day.day) !== from + d * 86400000 || !integer(day.count)) { return false; }
      total += day.count;
    }
    if (!integer(total) || total !== data.total) { return false; }
    if (data.downloads !== undefined) {
      var downloads = data.downloads, sumDownloads = 0, sumVersions = 0, versions = new Set();
      if (!downloads || !integer(downloads.total) || !Array.isArray(downloads.daily) || downloads.daily.length !== length || !Array.isArray(downloads.versions)) { return false; }
      for (var j = 0; j < length; j += 1) {
        var entry = downloads.daily[j];
        if (!entry || utcDay(entry.day) !== from + j * 86400000 || !integer(entry.count)) { return false; }
        sumDownloads += entry.count;
      }
      for (var k = 0; k < downloads.versions.length; k += 1) {
        var version = downloads.versions[k];
        if (!version || typeof version.value !== 'string' || version.value.length > 64 ||
            !/^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/.test(version.value) ||
            !integer(version.count) || version.count === 0 || versions.has(version.value)) { return false; }
        versions.add(version.value); sumVersions += version.count;
      }
      if (!integer(sumDownloads) || !integer(sumVersions) || sumDownloads !== downloads.total || sumVersions !== downloads.total) { return false; }
    }
    return Object.keys(dimensions).every(function (name) {
      var rows = data[name];
      if (!Array.isArray(rows)) { return false; }
      var seen = new Set(), sum = 0, previous = null;
      for (var i = 0; i < rows.length; i += 1) {
        var row = rows[i];
        if (!row || typeof row.value !== "string" || !integer(row.count) || row.count === 0 || seen.has(row.value)) { return false; }
        if (name === "pages" ? !page(row.value) : name === "languages" ? !language(row.value) : dimensions[name].indexOf(row.value) === -1) { return false; }
        if (previous && (row.count > previous.count || (row.count === previous.count && row.value < previous.value))) { return false; }
        seen.add(row.value);
        sum += row.count;
        previous = row;
      }
      return integer(sum) && sum === data.total;
    });
  }
  function node(tag, text) {
    var result = document.createElement(tag);
    if (text !== undefined) { result.textContent = text; }
    return result;
  }
  function table(name, rows) {
    var body = element(name);
    body.replaceChildren();
    if (!rows.length) {
      var empty = node("td", copy.empty);
      empty.setAttribute("colspan", "2");
      var emptyRow = node("tr");
      emptyRow.appendChild(empty);
      body.appendChild(emptyRow);
      return;
    }
    rows.forEach(function (row) {
      var tr = node("tr"), heading = node("th");
      heading.setAttribute("scope", "row");
      var value = name === "daily" ? row.day : row.value;
      if (name === "pages") {
        var link = node("a", value);
        link.setAttribute("href", value);
        heading.appendChild(link);
      } else {
        heading.textContent = copy[(prefixes[name] || "") + value] || value;
      }
      tr.appendChild(heading);
      tr.appendChild(node("td", String(row.count)));
      body.appendChild(tr);
    });
  }
  function svg(tag, attributes, text) {
    var result = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attributes).forEach(function (key) { result.setAttribute(key, String(attributes[key])); });
    if (text !== undefined) { result.textContent = text; }
    return result;
  }
  var chartRows = null;
  function chart(rows) {
    var chartNode = element("chart"), max = rows.reduce(function (value, row) { return Math.max(value, row.count); }, 0);
    var width = Math.max(260, chartNode.clientWidth || 1000), right = width - 10;
    var unit = (width - 20) / rows.length;
    chartRows = rows;
    chartNode.setAttribute("viewBox", "0 0 " + width + " 180");
    chartNode.replaceChildren();
    chartNode.appendChild(svg("title", {}, copy.daily));
    chartNode.appendChild(svg("line", {x1: 10, y1: 150, x2: right, y2: 150}));
    chartNode.appendChild(svg("text", {x: 10, y: 15}, String(max)));
    rows.forEach(function (row, i) {
      var height = max ? 120 * row.count / max : 0;
      var bar = svg("rect", {x: 10 + i * unit, y: 150 - height, width: Math.max(1, unit - 1), height: height});
      bar.appendChild(svg("title", {}, row.day + " · " + row.count));
      chartNode.appendChild(bar);
    });
    chartNode.appendChild(svg("text", {x: 10, y: 176, "text-anchor": "start"}, rows[0].day));
    chartNode.appendChild(svg("text", {x: right, y: 176, "text-anchor": "end"}, rows[rows.length - 1].day));
  }
  function render(data) {
    element("total").textContent = String(data.total);
    element("download-total").textContent = data.downloads ? String(data.downloads.total) : "—";
    element("window").textContent = copy.range.replace("{from}", data.window.from).replace("{to}", data.window.to);
    table("daily", data.daily);
    Object.keys(dimensions).forEach(function (name) { table(name, data[name]); });
    results.hidden = false;
    chart(data.daily);
    status.textContent = data.total === 0 ? "" : copy.ready;
  }
  var generation = 0, active = null;
  function visible() { return document.visibilityState !== "hidden"; }
  function load() {
    var days = selector.value === "all" ? "all" : Number(selector.value);
    if (!visible() || windows.indexOf(days) === -1) { return; }
    generation += 1;
    var request = generation;
    if (active) { active.cancel(); }
    var controller = new AbortController();
    var pending = true;
    function finish() {
      pending = false;
      window.clearTimeout(timer);
      if (request === generation) { active = null; }
    }
    function cancel() { controller.abort(); finish(); }
    var timer = window.setTimeout(function () {
      cancel();
      if (request === generation) { unavailable("unavailable"); root.setAttribute("aria-busy", "false"); }
    }, 10000);
    active = {cancel: cancel};
    unavailable("loading");
    root.setAttribute("aria-busy", "true");
    try {
      fetch("/api/stats/data?days=" + days, {
        method: "GET", mode: "same-origin", credentials: "omit", referrerPolicy: "no-referrer",
        cache: "no-store", signal: controller.signal
      }).then(function (response) {
        if (!response.ok) { throw new Error("Unavailable"); }
        return response.json();
      }).then(function (data) {
        if (!pending || request !== generation) { return; }
        if (data && data.enabled === false) { unavailable("disabled"); }
        else if (valid(data, days)) { render(data); }
        else { unavailable("unavailable"); }
      }).catch(function () {
        if (pending && request === generation) { unavailable("unavailable"); }
      }).finally(function () {
        if (pending) { finish(); }
        if (request === generation) { root.setAttribute("aria-busy", "false"); }
      });
    } catch (_) {
      finish();
      root.setAttribute("aria-busy", "false");
      unavailable("unavailable");
    }
  }
  selector.addEventListener("change", load);
  window.addEventListener("resize", function () { if (chartRows && !results.hidden) { chart(chartRows); } });
  element("refresh").addEventListener("click", load);
  document.addEventListener("visibilitychange", function () { if (visible() && !active) { load(); } });
  element("controls").hidden = false;
  window.setInterval(function () { if (visible() && !active) { load(); } }, 60000);
  if (visible()) { load(); }
}());
