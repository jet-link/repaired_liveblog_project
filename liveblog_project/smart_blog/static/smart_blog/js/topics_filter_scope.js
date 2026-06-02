/**
 * Topics list chip filter — session scope (all public pages).
 * Clears stored filter when the user is not on /topics or /topics/<slug>/.
 * topics_filter.js restores the chip on /topics/ only while storage remains.
 */
(function () {
  'use strict';

  var TOPICS_LIST_FILTER_KEY = 'topics_list_chip_filter';

  function topicsPathKind(pathname) {
    var p = (pathname || '').replace(/\/+$/, '') || '/';
    if (p === '/topics') return 'list';
    if (/^\/topics\/[^/]+$/.test(p)) return 'detail';
    return null;
  }

  function clearTopicsListFilterStorage() {
    try {
      sessionStorage.removeItem(TOPICS_LIST_FILTER_KEY);
    } catch (e) { /* ignore */ }
  }

  function syncTopicsFilterScope() {
    if (!topicsPathKind(window.location.pathname)) {
      clearTopicsListFilterStorage();
    }
  }

  window.TopicsFilterScope = {
    key: TOPICS_LIST_FILTER_KEY,
    pathKind: topicsPathKind,
    clear: clearTopicsListFilterStorage,
    isTopicsPage: function () {
      return !!topicsPathKind(window.location.pathname);
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncTopicsFilterScope);
  } else {
    syncTopicsFilterScope();
  }
  (document.documentElement || document).addEventListener('turbo:load', syncTopicsFilterScope);
})();
