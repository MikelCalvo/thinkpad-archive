/* Local progressive navigation: URL state, no fetch or HTML injection. */
(function () {
  "use strict";
  var form = document.getElementById("filters");
  var search = document.getElementById("model-search");
  var family = document.getElementById("family-filter");
  var drivers = document.getElementById("driver-filter");
  var manuals = document.getElementById("manual-filter");
  var empty = document.getElementById("empty-results");
  var body = document.getElementById("model-rows");
  if (!form || !search || !family || !drivers || !manuals || !empty || !body) { return; }
  var rows = body.getElementsByTagName("tr");
  var timeline = document.getElementById("timeline");
  var slider = document.getElementById("year-slider");
  var label = document.getElementById("selected-year");
  // Keep the static fallback immutable: update() changes the DOM attribute.
  var staticYear = timeline ? timeline.getAttribute("data-selected-year") || "all" : "all";
  var selected = staticYear;
  var links = timeline ? document.querySelectorAll("[data-year]") : [];
  var pending = null;
  var timer = null;
  var owned = ["q", "family", "drivers", "manuals", "year"];
  function hasURL() {
    return window.location && typeof window.URLSearchParams === "function";
  }
  function optionValue(control, value) {
    var options = control.options || [];
    for (var i = 0; i < options.length; i += 1) {
      if (options[i].value === value) { return value; }
    }
    return "";
  }
  function validYear(year) {
    if (year === "all") { return true; }
    for (var i = 0; i < links.length; i += 1) {
      if (links[i].getAttribute("data-year") === year && (year === "unknown" || /^\d{4}$/.test(year))) { return true; }
    }
    if (year === "unknown") {
      if (staticYear === "unknown") { return true; }
      for (var r = 0; r < rows.length; r += 1) {
        if (!rows[r].getAttribute("data-years") || rows[r].getAttribute("data-unknown-year") === "true") { return true; }
      }
    }
    return false;
  }
  function clearFilters() {
    search.value = "";
    family.value = "";
    drivers.value = "";
    manuals.value = "";
  }
  function state() {
    return {year:selected, q:search.value, family:family.value, drivers:drivers.value, manuals:manuals.value};
  }
  function readURL() {
    if (!hasURL()) { return; }
    var params = new window.URLSearchParams(window.location.search || "");
    var year = params.get("year");
    selected = validYear(year) ? year : staticYear;
    clearFilters();
    if (selected === "all") {
      search.value = params.get("q") || "";
      family.value = optionValue(family, params.get("family"));
      drivers.value = optionValue(drivers, params.get("drivers"));
      manuals.value = optionValue(manuals, params.get("manuals"));
    }
  }
  function writeURL(value, method) {
    if (!hasURL() || !window.history || typeof window.history[method] !== "function") { return; }
    try {
      // Keep unrelated query components byte-for-byte (including repeats).
      var raw = (window.location.search || "").replace(/^\?/, "").split("&");
      var parts = [];
      for (var i = 0; i < raw.length; i += 1) {
        if (!raw[i]) { continue; }
        var key = raw[i].split("=", 1)[0];
        try { key = decodeURIComponent(key.replace(/\+/g, " ")); }
        catch (_) { /* A malformed unrelated name must not block URL updates. */ }
        if (owned.indexOf(key) === -1) { parts.push(raw[i]); }
      }
      var params = new window.URLSearchParams();
      if (value.year === "all") {
        if (value.q.trim()) { params.set("q", value.q); }
        if (value.family) { params.set("family", value.family); }
        if (value.drivers) { params.set("drivers", value.drivers); }
        if (value.manuals) { params.set("manuals", value.manuals); }
      }
      if (value.year !== staticYear) { params.set("year", value.year); }
      var query = params.toString();
      if (query) { parts.push(query); }
      var nextSearch = parts.length ? "?" + parts.join("&") : "";
      if (nextSearch === (window.location.search || "")) { return; }
      window.history[method](null, "", (window.location.pathname || "") + nextSearch + (window.location.hash || ""));
    } catch (_) { /* file: URLs and restricted History still allow filtering. */ }
  }
  function cancelPending() {
    if (timer !== null && window.clearTimeout) { window.clearTimeout(timer); }
    timer = null;
    pending = null;
  }
  function flushPending() {
    var value = pending;
    cancelPending();
    if (value) { writeURL(value, "replaceState"); }
  }
  function normalized(value) {
    value = value.toLowerCase();
    if (value.normalize) { value = value.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); }
    return value;
  }
  function update() {
    var query = normalized(search.value).trim();
    var tokens = query ? query.split(/\s+/) : [];
    form.hidden = selected !== "all";
    var visible = 0;
    var activeYear = selected;
    for (var i = 0; i < rows.length; i += 1) {
      var row = rows[i];
      var haystack = normalized(row.getAttribute("data-search"));
      var years = row.getAttribute("data-years") || "";
      var yearMatch = activeYear === "all" || (activeYear === "unknown" ? (!years || row.getAttribute("data-unknown-year") === "true") : (" " + years + " ").indexOf(" " + activeYear + " ") !== -1);
      var match = yearMatch && (!family.value || row.getAttribute("data-family") === family.value) &&
        (!drivers.value || row.getAttribute("data-drivers") === drivers.value) &&
        (!manuals.value || row.getAttribute("data-manuals") === manuals.value);
      for (var j = 0; j < tokens.length && match; j += 1) {
        match = haystack.indexOf(tokens[j]) !== -1;
      }
      row.hidden = !match;
      if (match) { visible += 1; }
    }
    empty.hidden = visible !== 0;
    if (timeline) {
      timeline.setAttribute("data-selected-year", activeYear);
      if (label) {
        label.textContent = activeYear === "all" ? timeline.getAttribute("data-all-label") : activeYear === "unknown" ? timeline.getAttribute("data-unknown-label") : timeline.getAttribute("data-year-label") + " " + activeYear;
      }
      for (var n = 0; n < links.length; n += 1) {
        links[n].setAttribute("aria-current", links[n].getAttribute("data-year") === activeYear ? "true" : "false");
      }
      var languageLinks = document.querySelectorAll("[data-year-url]");
      for (var l = 0; l < languageLinks.length; l += 1) {
        var languageLink = languageLinks[l];
        languageLink.setAttribute("href", activeYear === "all" ? languageLink.getAttribute("data-all-url") : languageLink.getAttribute("data-year-url").replace("__year__", activeYear));
      }
      if (slider) {
        slider.value = /^\d{4}$/.test(activeYear) ? activeYear : timeline.getAttribute("data-all-value");
        slider.setAttribute("aria-valuetext", label ? label.textContent : activeYear);
      }
    }
  }
  function centerYear(link, smooth) {
    var rail = link.parentNode;
    if (!rail || !rail.getBoundingClientRect || !link.getBoundingClientRect) { return; }
    var railBox = rail.getBoundingClientRect();
    var linkBox = link.getBoundingClientRect();
    var left = rail.scrollLeft + linkBox.left - railBox.left - rail.clientLeft + linkBox.width / 2 - rail.clientWidth / 2;
    left = Math.max(0, Math.min(left, rail.scrollWidth - rail.clientWidth));
    var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (rail.scrollTo) {
      rail.scrollTo({left:left, behavior:smooth && !reducedMotion ? "smooth" : "auto"});
    } else {
      rail.scrollLeft = left;
    }
  }
  function centerSelected(smooth) {
    for (var n = 0; n < links.length; n += 1) {
      if (links[n].getAttribute("data-year") === selected) { centerYear(links[n], smooth); }
    }
  }
  function choose(year, scroll, smooth, method) {
    if (!validYear(year)) { return; }
    flushPending();
    selected = year;
    clearFilters();
    update();
    writeURL(state(), method || "pushState");
    if (scroll) { centerSelected(smooth); }
  }
  for (var k = 0; k < links.length; k += 1) {
    (function (link) {
      link.addEventListener("click", function (event) {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) { return; }
        event.preventDefault();
        choose(link.getAttribute("data-year"), true, true);
      });
    }(links[k]));
  }
  if (slider) {
    slider.hidden = false;
    slider.addEventListener("input", function () { choose(slider.value === timeline.getAttribute("data-all-value") ? "all" : slider.value, true, false, "replaceState"); });
  }
  form.addEventListener("submit", function (event) { event.preventDefault(); flushPending(); });
  search.addEventListener("input", function () {
    update();
    cancelPending();
    pending = state();
    timer = window.setTimeout(flushPending, 200);
  });
  function filterChanged() {
    flushPending();
    update();
    writeURL(state(), "pushState");
  }
  family.addEventListener("change", filterChanged);
  drivers.addEventListener("change", filterChanged);
  manuals.addEventListener("change", filterChanged);
  form.addEventListener("reset", function () {
    flushPending();
    selected = timeline ? timeline.getAttribute("data-default-year") || "all" : "all";
    // Reset fires before the browser resets the controls to their defaults.
    window.setTimeout(function () {
      clearFilters();
      update();
      writeURL(state(), "pushState");
      centerSelected(false);
    }, 0);
  });
  if (document.addEventListener) {
    // Capture runs before language.js copies the query, and before model links
    // navigate. Never prevent navigation or write one entry per keystroke.
    document.addEventListener("click", flushPending, true);
  }
  if (window.addEventListener) {
    window.addEventListener("pagehide", flushPending);
    window.addEventListener("popstate", function () {
      cancelPending();
      readURL();
      update();
      centerSelected(false);
    });
  }
  readURL();
  update();
  writeURL(state(), "replaceState");
}());
