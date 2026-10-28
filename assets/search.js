/* Local progressive navigation: no fetch, persistence or HTML injection. */
(function () {
  "use strict";
  var form = document.getElementById("filters");
  var search = document.getElementById("model-search");
  var family = document.getElementById("family-filter");
  var drivers = document.getElementById("driver-filter");
  var manuals = document.getElementById("manual-filter");
  var count = document.getElementById("result-count");
  var empty = document.getElementById("empty-results");
  var body = document.getElementById("model-rows");
  if (!form || !search || !family || !drivers || !manuals || !count || !empty || !body) { return; }
  var rows = body.getElementsByTagName("tr");
  var timeline = document.getElementById("timeline");
  var slider = document.getElementById("year-slider");
  var label = document.getElementById("selected-year");
  var selected = timeline ? timeline.getAttribute("data-selected-year") : "all";
  var links = timeline ? document.querySelectorAll("[data-year]") : [];
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
    count.textContent = String(visible);
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
  function choose(year, scroll, smooth) {
    selected = year;
    search.value = "";
    family.value = "";
    drivers.value = "";
    manuals.value = "";
    update();
    if (scroll) {
      for (var n = 0; n < links.length; n += 1) {
        if (links[n].getAttribute("data-year") === year) {
          centerYear(links[n], smooth);
        }
      }
    }
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
    slider.addEventListener("input", function () { choose(slider.value === timeline.getAttribute("data-all-value") ? "all" : slider.value, true); });
  }
  form.addEventListener("submit", function (event) { event.preventDefault(); });
  search.addEventListener("input", update);
  family.addEventListener("change", update);
  drivers.addEventListener("change", update);
  manuals.addEventListener("change", update);
  form.addEventListener("reset", function () {
    if (timeline) { selected = timeline.getAttribute("data-default-year"); }
    window.setTimeout(update, 0);
  });
  update();
}());
