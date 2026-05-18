(function () {
  'use strict';

  if (window.__themePickerInitialized) return;
  window.__themePickerInitialized = true;

  var PREF_KEY = 'themePreference';
  var LEGACY_KEY = 'themeToggle';

  var systemMql = null;
  var onSystemChange = null;

  function getStoredPreference() {
    var pref = null;
    try {
      pref = localStorage.getItem(PREF_KEY);
    } catch (e) { /* ignore */ }
    if (pref === 'light' || pref === 'dark' || pref === 'auto') return pref;

    var leg = null;
    try {
      leg = localStorage.getItem(LEGACY_KEY);
    } catch (e) { /* ignore */ }
    if (leg === 'sun') return 'dark';
    if (leg === 'moon') return 'light';
    return 'light';
  }

  function isDarkEffective(pref) {
    if (pref === 'dark') return true;
    if (pref === 'light') return false;
    try {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch (e) {
      return false;
    }
  }

  function applyDomTheme(pref) {
    var dark = isDarkEffective(pref);
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    syncThemeColorMeta();
  }

  function persistPreference(pref) {
    try {
      localStorage.setItem(PREF_KEY, pref);
      localStorage.removeItem(LEGACY_KEY);
    } catch (e) { /* ignore */ }
  }

  function syncThemeColorMeta() {
    var m = document.getElementById('meta-theme-color');
    if (!m) return;
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    m.setAttribute('content', dark ? '#0d1117' : '#ffffff');
  }

  function detachSystemListener() {
    if (systemMql && onSystemChange) {
      try {
        systemMql.removeEventListener('change', onSystemChange);
      } catch (e) {
        try {
          systemMql.removeListener(onSystemChange);
        } catch (e2) { /* ignore */ }
      }
    }
    systemMql = null;
    onSystemChange = null;
  }

  function attachSystemListenerIfAuto(pref) {
    detachSystemListener();
    if (pref !== 'auto') return;
    try {
      systemMql = window.matchMedia('(prefers-color-scheme: dark)');
    } catch (e) {
      return;
    }
    onSystemChange = function () {
      try {
        if (localStorage.getItem(PREF_KEY) !== 'auto') return;
      } catch (e) { /* ignore */ }
      applyDomTheme('auto');
      refreshCycleButtons();
    };
    try {
      systemMql.addEventListener('change', onSystemChange);
    } catch (e) {
      if (systemMql.addListener) systemMql.addListener(onSystemChange);
    }
  }

  function nextPreference(pref) {
    if (pref === 'light') return 'dark';
    if (pref === 'dark') return 'auto';
    return 'light';
  }

  function setPreference(pref) {
    if (pref !== 'light' && pref !== 'dark' && pref !== 'auto') pref = 'light';
    persistPreference(pref);
    applyDomTheme(pref);
    attachSystemListenerIfAuto(pref);
    refreshCycleButtons();
  }

  function refreshCycleButtons() {
    var pref = getStoredPreference();
    document.querySelectorAll('[data-theme-cycle]').forEach(function (btn) {
      btn.classList.remove('theme-pref-light', 'theme-pref-dark', 'theme-pref-auto');
      btn.classList.add('theme-pref-' + pref);
      var label =
        pref === 'light'
          ? 'Theme: Light'
          : pref === 'dark'
            ? 'Theme: Dark'
            : 'Theme: Auto (follows system)';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
    });
  }

  function init() {
    var pref = getStoredPreference();
    applyDomTheme(pref);
    attachSystemListenerIfAuto(pref);
    refreshCycleButtons();

    document.addEventListener(
      'click',
      function (e) {
        var btn =
          e.target && e.target.closest ? e.target.closest('[data-theme-cycle]') : null;
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        setPreference(nextPreference(getStoredPreference()));
      },
      true,
    );
  }

  document.documentElement.addEventListener('turbo:load', function () {
    var p = getStoredPreference();
    applyDomTheme(p);
    attachSystemListenerIfAuto(p);
    refreshCycleButtons();
    syncThemeColorMeta();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
