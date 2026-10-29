/* Software-only progressive filters. Original metadata and firmware stay intact. */
(function () {
  "use strict";
  var form = document.getElementById("package-filters");
  var section = document.getElementById("drivers");
  var search = document.getElementById("package-search");
  var system = document.getElementById("package-os");
  var empty = document.getElementById("package-empty");
  var status = document.getElementById("package-filter-status");
  if (!form || !section || !search || !system || !empty || !status) { return; }
  var rows = section.querySelectorAll("[data-package-search]");
  var categories = section.querySelectorAll(".driver-category");
  var before = null;
  function normalized(value) {
    value = value.toLowerCase();
    return value.normalize ? value.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : value;
  }
  function update() {
    var query = normalized(search.value).trim();
    var tokens = query ? query.split(/\s+/) : [];
    var active = !!(query || system.value);
    if (active && before === null) {
      before = [];
      for (var n = 0; n < categories.length; n += 1) { before.push(categories[n].open); }
    }
    var shown = 0;
    for (var i = 0; i < rows.length; i += 1) {
      var row = rows[i];
      var systems = JSON.parse(row.getAttribute("data-package-os"));
      var match = !system.value || (system.value === "__unrecorded__" ? !systems.length : systems.indexOf(system.value) !== -1);
      var haystack = normalized(row.getAttribute("data-package-search"));
      for (var j = 0; j < tokens.length && match; j += 1) { match = haystack.indexOf(tokens[j]) !== -1; }
      row.hidden = !match;
      if (match) { shown += 1; }
    }
    for (var c = 0; c < categories.length; c += 1) {
      var category = categories[c];
      var packages = category.querySelectorAll("[data-package-search]");
      var count = 0;
      for (var k = 0; k < packages.length; k += 1) { if (!packages[k].hidden) { count += 1; } }
      category.hidden = count === 0;
      category.querySelector(".category-count").textContent = active ? count + " / " + packages.length : String(packages.length);
      if (active) { category.open = count > 0; }
      else if (before !== null) { category.open = before[c]; }
    }
    if (!active) { before = null; }
    empty.hidden = shown !== 0;
    status.hidden = !active;
    status.textContent = status.getAttribute("data-pattern").replace("{shown}", String(shown)).replace("{total}", String(rows.length));
  }
  form.addEventListener("submit", function (event) { event.preventDefault(); });
  search.addEventListener("input", update);
  system.addEventListener("change", update);
  form.addEventListener("reset", function () { window.setTimeout(update, 0); });
  update();
  form.hidden = false;
}());
