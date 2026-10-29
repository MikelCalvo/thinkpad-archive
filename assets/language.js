/* Remember an explicit language choice; only the neutral entry follows it. */
(function () {
  "use strict";
  var key = "thinkpad-archive-language";
  var root = document.documentElement;
  var alternatives = document.querySelectorAll('link[rel="alternate"][hreflang]');
  var saved = null;
  function target(code) {
    for (var i = 0; i < alternatives.length; i += 1) {
      if (alternatives[i].getAttribute("hreflang") === code) {
        return alternatives[i].getAttribute("data-language-target") || alternatives[i].getAttribute("href");
      }
    }
    return null;
  }
  try { saved = localStorage.getItem(key); } catch (_) { /* Static links still work. */ }
  if (root.getAttribute("data-language-entry") === "true" && saved &&
      saved !== root.getAttribute("lang") && target(saved)) {
    window.location.replace(target(saved) + window.location.search + window.location.hash);
  }

  function connect() {
    var links = document.querySelectorAll("[data-language-choice]");
    var picker = document.getElementById("language-picker");
    for (var i = 0; i < links.length; i += 1) {
      (function (link) {
        link.addEventListener("click", function () {
          var code = link.getAttribute("data-language-choice");
          if (!target(code)) { return; }
          try { localStorage.setItem(key, code); } catch (_) { /* Navigation needs no storage. */ }
          // Read the current href: the timeline can have selected a different year.
          var href = link.getAttribute("href").split(/[?#]/)[0];
          link.setAttribute("href", href + window.location.search + window.location.hash);
          if (picker) { picker.open = false; }
        });
      }(links[i]));
    }
    if (picker) {
      document.addEventListener("click", function (event) {
        if (!picker.contains(event.target)) { picker.open = false; }
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && picker.open) {
          picker.open = false;
          picker.querySelector("summary").focus();
        }
      });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect);
  } else { connect(); }
}());
