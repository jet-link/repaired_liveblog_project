(function () {
  'use strict';

  function closestFromEventTarget(target, selector) {
    if (!target) return null;
    var el = target.nodeType === 1 ? target : target.parentElement;
    return el && el.closest ? el.closest(selector) : null;
  }

  function extraQueryString() {
    var el = document.getElementById('topicHubPageRoot');
    var raw = (el && el.dataset && el.dataset.topicPreserveQuery) || '';
    return String(raw).trim();
  }

  function buildPartialUrl(base, sort) {
    var u = base.indexOf('?') >= 0 ? base + '&' : base + '?';
    u += 'partial=1';
    var extra = extraQueryString();
    if (extra) {
      u += '&' + extra;
    }
    if (sort && sort !== 'latest') {
      u += '&sort=' + encodeURIComponent(sort);
    }
    return u;
  }

  function buildHistoryQuery(sort) {
    var parts = [];
    var extra = extraQueryString();
    if (extra) {
      parts.push(extra);
    }
    if (sort && sort !== 'latest') {
      parts.push('sort=' + encodeURIComponent(sort));
    }
    return parts.length ? '?' + parts.join('&') : '';
  }

  function replaceTopicFeed(html) {
    var root = document.getElementById('topicHubFeedRoot');
    var wrap = document.getElementById('filterCardsWrapper');
    if (!root || !wrap) return;
    wrap.classList.add('filter-cards-fade-out');
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        root.innerHTML = html;
        wrap.classList.remove('filter-cards-fade-out');
        wrap.classList.add('filter-cards-fade-in');
        wrap.offsetHeight;
        wrap.classList.remove('filter-cards-fade-in');
        if (window.initFilterCardsPagination) window.initFilterCardsPagination();
      });
    });
  }

  function setSelectedSort(sort) {
    document.querySelectorAll('.topic-sort-btn').forEach(function (btn) {
      btn.classList.toggle('is-selected', (btn.dataset.sort || '') === sort);
    });
  }

  function runSortFromButton(btn) {
    if (!btn || !document.getElementById('topicHubFeedRoot')) return;

    var sort = btn.dataset.sort || 'latest';
    var base = btn.dataset.topicBase || '';
    if (!base) return;

    var url = buildPartialUrl(base.replace(/\/?$/, '/'), sort);
    var reqId = (replaceTopicFeed._reqId = (replaceTopicFeed._reqId || 0) + 1);

    fetch(url, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      cache: 'no-store',
    })
      .then(function (r) {
        if (!r.ok) throw new Error('topic feed');
        return r.text();
      })
      .then(function (html) {
        if (reqId !== replaceTopicFeed._reqId) return;
        replaceTopicFeed(html);
        setSelectedSort(sort);
        if (typeof window.scrollFilterSegmentSelectedIntoView === 'function') {
          requestAnimationFrame(function () {
            requestAnimationFrame(window.scrollFilterSegmentSelectedIntoView);
          });
        }
        try {
          var path = base.replace(/\/?$/, '/');
          window.history.replaceState({}, '', path + buildHistoryQuery(sort));
        } catch (err) { /* ignore */ }
      })
      .catch(function () {
        if (window.__brainPreloader && typeof window.__brainPreloader.show === 'function') {
          window.__brainPreloader.show();
        }
        window.location.href = base.replace(/\/?$/, '/') + buildHistoryQuery(sort);
      });
  }

  function initTopicSortBar(bar) {
    if (!bar || !document.getElementById('topicHubFeedRoot')) return;

    var suppressNextClick = false;
    var pendingTap = null;

    bar.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
      pendingTap = { x: e.clientX, y: e.clientY, pid: e.pointerId };
    }, { passive: true });

    bar.addEventListener('pointercancel', function (e) {
      if (pendingTap && pendingTap.pid === e.pointerId) pendingTap = null;
    });

    bar.addEventListener('pointerup', function (e) {
      if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
      if (e.button !== 0) return;
      var start = pendingTap;
      pendingTap = null;
      if (!start || start.pid !== e.pointerId) return;
      var dx = Math.abs(e.clientX - start.x);
      var dy = Math.abs(e.clientY - start.y);
      if (dx > 14 || dy > 14) return;
      var btn = closestFromEventTarget(e.target, '.topic-sort-btn');
      if (!btn) return;
      runSortFromButton(btn);
      suppressNextClick = true;
      window.setTimeout(function () {
        suppressNextClick = false;
      }, 550);
    });

    bar.addEventListener('click', function (e) {
      if (suppressNextClick) {
        suppressNextClick = false;
        e.preventDefault();
        return;
      }
      var btn = closestFromEventTarget(e.target, '.topic-sort-btn');
      if (!btn) return;
      e.preventDefault();
      runSortFromButton(btn);
    });
  }

  function tryInitTopicSortBar() {
    var bar = document.getElementById('topicSortBar');
    if (!bar || !document.getElementById('topicHubFeedRoot')) return;
    if (bar.__topicSortBarBound) return;
    bar.__topicSortBarBound = true;
    initTopicSortBar(bar);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInitTopicSortBar);
  } else {
    tryInitTopicSortBar();
  }
  (document.documentElement || document).addEventListener('turbo:load', tryInitTopicSortBar);
})();
