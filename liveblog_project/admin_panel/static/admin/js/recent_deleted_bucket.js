/**
 * Bucket (recent deleted): tab / pagination without full page reload.
 */
(function () {
  'use strict';

  var PARTIAL_PARAM = 'partial';
  var ROOT_ID = 'recentDeletedBucketRoot';

  function bucketPathMatches(url) {
    try {
      var u = new URL(url, window.location.href);
      return u.pathname === window.location.pathname;
    } catch (e) {
      return false;
    }
  }

  function isBucketNavLink(anchor) {
    if (!anchor || anchor.getAttribute('href') == null) return false;
    if (!bucketPathMatches(anchor.href)) return false;
    var u = new URL(anchor.href, window.location.href);
    return u.searchParams.has('tab') || u.searchParams.has('page');
  }

  function fetchPartial(url) {
    var fetchUrl = new URL(url, window.location.href);
    fetchUrl.searchParams.set(PARTIAL_PARAM, '1');
    return fetch(fetchUrl.toString(), {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }).then(function (res) {
      if (res.status === 403) {
        window.location.assign(new URL(url, window.location.href).pathname);
        return null;
      }
      if (!res.ok) {
        window.location.assign(url);
        return null;
      }
      return res.text();
    });
  }

  function replaceBucket(html) {
    var wrap = document.getElementById(ROOT_ID);
    if (!wrap || !html) return;
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var next = doc.getElementById(ROOT_ID);
    if (!next) {
      window.location.reload();
      return;
    }
    if (document.activeElement && typeof document.activeElement.blur === 'function') {
      document.activeElement.blur();
    }
    var imported = document.importNode(next, true);
    wrap.replaceWith(imported);
    if (typeof window.adminInitBulkTablesIn === 'function') {
      window.adminInitBulkTablesIn(imported);
    }
    /* Same timing as Topics (topic_hub_sort / topics_filter): 2× rAF after layout.
       behavior: 'auto' — new .filter-segment-scroll resets scrollLeft; smooth() + focus on iOS caused snap-back. */
    if (typeof window.scrollFilterSegmentSelectedIntoView === 'function') {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          window.scrollFilterSegmentSelectedIntoView({ behavior: 'auto' });
        });
      });
    }
  }

  function pushHistory(url) {
    var u = new URL(url, window.location.href);
    u.searchParams.delete(PARTIAL_PARAM);
    try {
      history.pushState({ bucketAjax: true }, '', u.pathname + u.search + u.hash);
    } catch (e) {}
  }

  function onClick(e) {
    if (e.defaultPrevented) return;
    if (e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest('a');
    if (!a || !isBucketNavLink(a)) return;
    e.preventDefault();
    var href = a.getAttribute('href');
    fetchPartial(href).then(function (html) {
      if (html == null) return;
      replaceBucket(html);
      pushHistory(href);
    });
  }

  function onPopState() {
    fetchPartial(window.location.href).then(function (html) {
      if (html == null) return;
      replaceBucket(html);
    });
  }

  function bind() {
    document.addEventListener('click', onClick);
    window.addEventListener('popstate', onPopState);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
