/* Optional progressive enhancement: no fetch, no persistence, no HTML injection. */
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
  function normalized(value) {
    value = value.toLowerCase();
    if (value.normalize) { value = value.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); }
    return value;
  }
  function update() {
    var query = normalized(search.value).trim();
    var tokens = query ? query.split(/\s+/) : [];
    var visible = 0;
    for (var i = 0; i < rows.length; i += 1) {
      var row = rows[i];
      var haystack = normalized(row.getAttribute("data-search"));
      var match = (!family.value || row.getAttribute("data-family") === family.value) &&
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
  }
  form.addEventListener("submit", function (event) { event.preventDefault(); });
  search.addEventListener("input", update);
  family.addEventListener("change", update);
  drivers.addEventListener("change", update);
  manuals.addEventListener("change", update);
  form.addEventListener("reset", function () { window.setTimeout(update, 0); });
  form.hidden = false;
  update();
}());
