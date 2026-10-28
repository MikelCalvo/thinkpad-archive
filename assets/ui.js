/* Optional presentation only: no network, cookies or persistent preferences. */
(function () {
  "use strict";
  var jumps = document.querySelectorAll("[data-category-target]");
  for (var j = 0; j < jumps.length; j += 1) {
    (function (link) {
      link.addEventListener("click", function (event) {
        var target = document.getElementById(link.getAttribute("data-category-target"));
        if (!target) { return; }
        event.preventDefault();
        target.open = true;
        var summary = target.querySelector("summary");
        if (summary) { summary.focus({preventScroll:true}); }
        target.scrollIntoView({block:"start"});
      });
    }(jumps[j]));
  }
}());
