/**
 * Mindset profile (/profile/<user>/themes/): switch Themes / Reposts / Replies without full reload.
 * Fetch + swap `[data-profile-mindset-swap]` + history.pushState (similar idea to BraiNews filter AJAX).
 */
(function () {
  'use strict';

  var PAGE_SEL = '.profile-reposts-page';
  var SWAP_SEL = '[data-profile-mindset-swap]';
  var NAV_SEL = '.profile-mindset-tabs.filter-segment-bar';
  var LOADING_CLASS = 'profile-mindset-swap--loading';

  var abortCtrl = null;
  var basePathNorm = '';

  function normPath(urlStr) {
    try {
      var u = new URL(urlStr, window.location.origin);
      var p = u.pathname.replace(/\/+$/, '');
      return p || '/';
    } catch (_) {
      return '';
    }
  }

  function sameProfilePath(nav, clickedUrl) {
    if (!nav) return false;
    var first = nav.querySelector('a.filter-reason-btn[href]');
    if (!first) return false;
    return normPath(first.href) === normPath(clickedUrl);
  }

  function normalizeTab(tab) {
    var t = (tab || '').toLowerCase();
    if (t === 'root') return 'themes';
    if (t !== 'themes' && t !== 'reposts' && t !== 'replies') return 'themes';
    return t;
  }

  function syncTabSelection(nav, fullUrl) {
    if (!nav) return;
    var tabParam = 'themes';
    try {
      tabParam = normalizeTab(new URL(fullUrl, window.location.origin).searchParams.get('tab'));
    } catch (_) {}

    nav.querySelectorAll('a.filter-reason-btn').forEach(function (a) {
      var lt = 'themes';
      try {
        lt = normalizeTab(new URL(a.getAttribute('href') || '', window.location.origin).searchParams.get('tab'));
      } catch (_) {}

      var sel = lt === tabParam;
      a.classList.toggle('is-selected', sel);
      if (sel) {
        a.setAttribute('aria-current', 'page');
      } else {
        a.removeAttribute('aria-current');
      }
    });
  }

  function updateTitle(parsedDoc) {
    var nt = parsedDoc.querySelector('title');
    if (nt && nt.textContent) {
      document.title = nt.textContent.trim();
    }
  }

  function afterSwap() {
    requestAnimationFrame(function () {
      if (typeof window.scrollFilterSegmentSelectedIntoView === 'function') {
        window.scrollFilterSegmentSelectedIntoView({ behavior: 'auto' });
      }
      if (typeof window.updateFilterSegmentEvenMobile === 'function') {
        window.updateFilterSegmentEvenMobile();
      }
    });
  }

  function swapFromHtml(htmlText, resolvedUrl, swapEl, nav) {
    var doc;
    try {
      doc = new DOMParser().parseFromString(htmlText, 'text/html');
    } catch (_) {
      return false;
    }
    var incoming = doc.querySelector(SWAP_SEL);
    if (!incoming || !incoming.innerHTML) {
      return false;
    }
    swapEl.innerHTML = incoming.innerHTML;
    syncTabSelection(nav, resolvedUrl);
    updateTitle(doc);
    afterSwap();
    return true;
  }

  /**
   * @param {string} url
   * @param {{ skipPushState?: boolean }} [opts]
   */
  function go(url, opts) {
    opts = opts || {};

    var root = document.querySelector(PAGE_SEL);
    if (!root) return Promise.resolve(false);
    var swapEl = root.querySelector(SWAP_SEL);
    var nav = root.querySelector(NAV_SEL);
    if (!swapEl || !nav) return Promise.resolve(false);

    swapEl.classList.add(LOADING_CLASS);

    if (abortCtrl) {
      abortCtrl.abort();
    }
    abortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null;

    return fetch(url, {
      credentials: 'same-origin',
      signal: abortCtrl ? abortCtrl.signal : undefined,
      headers: {
        Accept: 'text/html',
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(function (res) {
        if (!res.ok) throw new Error('bad_status');
        return res.text();
      })
      .then(function (html) {
        if (!swapFromHtml(html, url, swapEl, nav)) {
          throw new Error('parse_swap');
        }
        if (!opts.skipPushState) {
          history.pushState({ profileMindsetTabs: true }, '', url);
        }
        return true;
      })
      .catch(function () {
        window.location.assign(url);
        return false;
      })
      .finally(function () {
        swapEl.classList.remove(LOADING_CLASS);
      });
  }

  function onClick(e) {
    var root = document.querySelector(PAGE_SEL);
    if (!root) return;
    var nav = root.querySelector(NAV_SEL);
    if (!nav || !nav.contains(e.target)) return;

    var anchor = e.target.closest('a.filter-reason-btn');
    if (!anchor || !anchor.getAttribute('href')) return;

    if (e.defaultPrevented) return;
    if (e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    try {
      var full = new URL(anchor.href, window.location.origin).href;
      var cur = window.location.href.split('#')[0];
      if (full === cur) {
        e.preventDefault();
        return;
      }
    } catch (_) {
      return;
    }

    if (!sameProfilePath(nav, anchor.href)) return;

    e.preventDefault();

    if (typeof window.scrollPageToTopForListingFilter === 'function') {
      window.scrollPageToTopForListingFilter();
    }

    try {
      go(new URL(anchor.href, window.location.origin).href, {});
    } catch (_) {
      window.location.assign(anchor.href);
    }
  }

  function onPopState() {
    var root = document.querySelector(PAGE_SEL);
    if (!root) return;
    if (normPath(window.location.pathname) !== basePathNorm) return;
    go(window.location.href, { skipPushState: true });
  }

  function init() {
    var root = document.querySelector(PAGE_SEL);
    if (!root || root.dataset.profileMindsetTabsBound === '1') return;
    var nav = root.querySelector(NAV_SEL);
    if (!nav || !nav.querySelector('a.filter-reason-btn')) return;

    basePathNorm = normPath(window.location.pathname);
    root.dataset.profileMindsetTabsBound = '1';

    root.addEventListener('click', onClick);
    window.addEventListener('popstate', onPopState);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
