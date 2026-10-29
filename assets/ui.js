/* Optional category presentation: no network or persistent state. */
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
  var copyButton = document.getElementById("offline-copy");
  var hash = document.getElementById("offline-hash");
  var copyStatus = document.getElementById("offline-copy-status");
  if (!copyButton || !hash || !copyStatus) { return; }
  var resetTimer = null;
  function resetCopy() {
    copyButton.classList.remove("is-copied");
    copyButton.setAttribute("aria-label", copyButton.getAttribute("data-copy-label"));
    copyButton.setAttribute("title", copyButton.getAttribute("data-copy-label"));
    copyStatus.textContent = "";
  }
  function legacyCopy() {
    hash.focus();
    hash.select();
    if (!document.execCommand || !document.execCommand("copy")) { throw new Error("Copy unavailable"); }
    copyButton.focus({preventScroll:true});
  }
  copyButton.hidden = false;
  copyButton.addEventListener("click", function () {
    if (copyButton.disabled) { return; }
    window.clearTimeout(resetTimer);
    resetCopy();
    copyButton.disabled = true;
    var operation;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        operation = navigator.clipboard.writeText(hash.value).catch(legacyCopy);
      } else {
        legacyCopy();
        operation = Promise.resolve();
      }
    } catch (_) { operation = Promise.reject(_); }
    operation.then(function () {
      copyButton.classList.add("is-copied");
      var label = copyButton.getAttribute("data-copied-label");
      copyButton.setAttribute("aria-label", label);
      copyButton.setAttribute("title", label);
      copyStatus.textContent = label;
      resetTimer = window.setTimeout(resetCopy, 2000);
    }).catch(function () {
      copyStatus.textContent = copyButton.getAttribute("data-copy-failed");
    }).then(function () { copyButton.disabled = false; });
  });
}());
