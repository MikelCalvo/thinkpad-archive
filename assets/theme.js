/* Dark by default; a saved local preference is applied before CSS. */
(function () {
  "use strict";
  var key = "thinkpad-archive-theme";
  var root = document.documentElement;
  var preference = null;
  var button;

  function valid(value) { return value === "dark" || value === "light"; }
  try {
    var saved = localStorage.getItem(key);
    if (valid(saved)) { preference = saved; }
  } catch (_) { /* Storage may be disabled, including under file://. */ }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    if (button) {
      var label = button.getAttribute(theme === "dark" ? "data-light-label" : "data-dark-label");
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
    }
  }
  apply(preference || "dark");

  function connect() {
    button = document.getElementById("theme-toggle");
    if (!button) { return; }
    apply(root.getAttribute("data-theme"));
    button.hidden = false;
    button.addEventListener("click", function () {
      preference = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      apply(preference);
      try { localStorage.setItem(key, preference); } catch (_) { /* Keep this tab usable. */ }
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect);
  } else { connect(); }

  window.addEventListener("storage", function (event) {
    if (event.key !== key && event.key !== null) { return; }
    preference = valid(event.newValue) ? event.newValue : null;
    apply(preference || "dark");
  });
}());
