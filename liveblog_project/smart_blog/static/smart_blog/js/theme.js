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
      refreshToggleButtonFace();
    };
    try {
      systemMql.addEventListener('change', onSystemChange);
    } catch (e) {
      if (systemMql.addListener) systemMql.addListener(onSystemChange);
    }
  }

  function setPreference(pref) {
    if (pref !== 'light' && pref !== 'dark' && pref !== 'auto') pref = 'light';
    persistPreference(pref);
    applyDomTheme(pref);
    attachSystemListenerIfAuto(pref);
    refreshToggleButtonFace();
    syncMenuActiveState();
  }

  function refreshToggleButtonFace() {
    var btn = document.getElementById('themeToggle');
    if (!btn) return;
    var pref = getStoredPreference();
    btn.classList.toggle('theme-toggle-btn--auto', pref === 'auto');
  }

  function syncMenuActiveState() {
    var pref = getStoredPreference();
    document.querySelectorAll('.theme-tooltip-option[data-theme-pref]').forEach(function (el) {
      var p = el.getAttribute('data-theme-pref');
      el.classList.toggle('is-active', p === pref);
    });
  }

  function closeThemeMenu() {
    var menu = document.getElementById('themeMenu');
    var btn = document.getElementById('themeToggle');
    if (menu) menu.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function openThemeMenu() {
    var menu = document.getElementById('themeMenu');
    var btn = document.getElementById('themeToggle');
    if (!menu || !btn) return;
    var userMenu = document.getElementById('userMenu');
    if (userMenu) userMenu.classList.remove('open');
    menu.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    updateThemeTooltipCaret();
    syncMenuActiveState();
  }

  function toggleThemeMenu() {
    var menu = document.getElementById('themeMenu');
    if (!menu) return;
    if (menu.classList.contains('open')) closeThemeMenu();
    else openThemeMenu();
  }

  function updateThemeTooltipCaret() {
    var menu = document.getElementById('themeMenu');
    var btn = document.getElementById('themeToggle');
    var tooltip = menu && menu.querySelector('.theme-tooltip');
    if (!menu || !btn || !tooltip || !menu.classList.contains('open')) return;
    var ar = btn.getBoundingClientRect();
    var tr = tooltip.getBoundingClientRect();
    var x = ar.left + ar.width / 2 - tr.left;
    tooltip.style.setProperty('--theme-tooltip-caret-x', x + 'px');
  }

  function init() {
    var pref = getStoredPreference();
    applyDomTheme(pref);
    attachSystemListenerIfAuto(pref);
    refreshToggleButtonFace();
    syncMenuActiveState();

    document.addEventListener(
      'click',
      function (e) {
        var menu = document.getElementById('themeMenu');
        if (!menu) return;
        if (!menu.contains(e.target)) closeThemeMenu();
      },
      true,
    );

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeThemeMenu();
    });

    window.addEventListener(
      'scroll',
      function () {
        closeThemeMenu();
      },
      { passive: true },
    );

    window.addEventListener(
      'resize',
      function () {
        updateThemeTooltipCaret();
      },
      { passive: true },
    );

    document.addEventListener(
      'click',
      function (e) {
        var opt =
          e.target && e.target.closest ? e.target.closest('.theme-tooltip-option[data-theme-pref]') : null;
        var menu = document.getElementById('themeMenu');
        if (!opt || !menu || !menu.contains(opt)) return;
        e.preventDefault();
        var nextPref = opt.getAttribute('data-theme-pref');
        setPreference(nextPref);
        closeThemeMenu();
      },
      true,
    );

    document.addEventListener(
      'click',
      function (e) {
        var t = e.target && e.target.closest ? e.target.closest('#themeToggle') : null;
        var menu = document.getElementById('themeMenu');
        if (!menu || !t || !menu.contains(t)) return;
        e.preventDefault();
        e.stopPropagation();
        toggleThemeMenu();
        if (menu.classList.contains('open')) {
          requestAnimationFrame(function () {
            requestAnimationFrame(updateThemeTooltipCaret);
          });
        }
      },
      true,
    );
  }

  document.documentElement.addEventListener('turbo:load', function () {
    var p = getStoredPreference();
    applyDomTheme(p);
    attachSystemListenerIfAuto(p);
    refreshToggleButtonFace();
    syncMenuActiveState();
    syncThemeColorMeta();
    closeThemeMenu();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
