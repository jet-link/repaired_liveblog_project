/**
 * Polls /api/trending/ every 5s (page 1 only) and updates .trending-val metrics.
 * Displays numbers in human-readable format (1K, 15K, 1.2M).
 */
(function () {
  var root = document.getElementById("trendingPageRoot");
  if (!root) return;
  var baseUrl = root.dataset.trendingApiUrl;
  if (!baseUrl) return;

  var statusEl = document.getElementById("trendingPollStatus");
  var params = new URLSearchParams(window.location.search);
  var page = params.get("page") || "1";
  if (page !== "1") {
    if (statusEl) statusEl.textContent = "";
    return;
  }

  function humanize(n) {
    n = Number(n);
    if (isNaN(n)) return "0";
    if (n < 1000) return String(n);
    var tiers = [
      [1e9, "B"],
      [1e6, "M"],
      [1e3, "K"],
    ];
    for (var i = 0; i < tiers.length; i++) {
      var threshold = tiers[i][0];
      var suffix = tiers[i][1];
      if (n >= threshold) {
        var val = n / threshold;
        if (val >= 10) return Math.floor(val) + suffix;
        var truncated = Math.floor(val * 10) / 10;
        var str = truncated.toFixed(1).replace(/\.0$/, "");
        return str + suffix;
      }
    }
    return String(n);
  }

  var HUMANIZE_NUMERIC_KEYS = {
    views_24h: true,
    likes_24h: true,
    comments_24h: true,
    bookmarks_24h: true,
    reposts_24h: true,
    views_last_hour: true,
    likes_1h: true,
    comments_1h: true,
  };

  function mergeRows(data) {
    var map = {};
    ["hot", "rising", "feed"].forEach(function (k) {
      (data[k] || []).forEach(function (row) {
        if (row.slug) map[row.slug] = row;
      });
    });
    return map;
  }

  function applyRow(slug, row) {
    var containers = document.querySelectorAll(
      '[data-trending-slug="' + slug + '"]'
    );
    containers.forEach(function (container) {
      container.querySelectorAll("[data-metric]").forEach(function (el) {
        var key = el.getAttribute("data-metric");
        if (!key || row[key] === undefined) return;
        var valNode = el.querySelector(".trending-val");
        var raw = row[key];
        var display = HUMANIZE_NUMERIC_KEYS[key] ? humanize(raw) : String(raw);
        if (valNode) valNode.textContent = display;
        else el.textContent = display;
      });
    });
  }

  async function poll() {
    try {
      var res = await fetch(baseUrl + "?page=1", { credentials: "same-origin" });
      if (!res.ok) return;
      var data = await res.json();
      if (!data.ok && data.hot === undefined) return;
      var map = mergeRows(data);
      Object.keys(map).forEach(function (slug) {
        applyRow(slug, map[slug]);
      });
      if (statusEl) {
        statusEl.textContent =
          "Live · " +
          new Date().toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
      }
    } catch (e) {
      /* ignore */
    }
  }

  poll();
  setInterval(poll, 5000);
})();
