// Discord Token Manager marketing site helpers.

(function () {
  "use strict";

  // Update the release download links programmatically so the page works even
  // if we bump the tag, and so the downloads map to the latest release tag.
  var LATEST_TAG = "v1.0.0";
  var OWNER = "mnishantlabs";
  var REPO = "Discord-Multiple-VC-Joiner";

  function assetUrl(name) {
    return "https://github.com/" + OWNER + "/" + REPO +
      "/releases/download/" + LATEST_TAG + "/" + name;
  }

  var ASSETS = {
    "DiscordTokenManager-compact.exe": "DiscordTokenManager-compact.exe",
    "DiscordTokenManager-portable.zip": "DiscordTokenManager-portable.zip",
    "DiscordTokenManager-setup.exe": "DiscordTokenManager-setup.exe"
  };

  document.querySelectorAll("a[data-asset]").forEach(function (a) {
    var key = a.getAttribute("data-asset");
    if (ASSETS[key]) a.href = assetUrl(key);
  });

  var versionBadge = document.querySelector(".hero-badge");
  if (versionBadge && versionBadge.textContent.indexOf("v1.0.0") === -1) {
    versionBadge.textContent = versionBadge.textContent.replace(/v[\d.]+/, LATEST_TAG);
  }

  if (window.location.hash) {
    var el = document.querySelector(window.location.hash);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
})();