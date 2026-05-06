(function () {
  'use strict';

  if (window.__themeToggleInitialized) return;
  window.__themeToggleInitialized = true;

  var STORAGE_KEY = 'themeToggle';
  var ACTIVE_VAL = 'sun';

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }

  function isDark() {
    return getTheme() === 'dark';
  }

  function syncThemeColorMeta() {
    var m = document.getElementById('meta-theme-color');
    if (!m) return;
    m.setAttribute('content', isDark() ? '#0d1117' : '#ffffff');
  }

  function setTheme(dark) {
    var theme = dark ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, dark ? ACTIVE_VAL : 'moon');
    } catch (e) {}
    syncThemeColorMeta();
  }

  function handleToggle() {
    setTheme(!isDark());
  }

  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('#themeToggle, .theme-toggle-btn') : null;
    if (!t) return;
    e.preventDefault();
    handleToggle();
  }, true);

  syncThemeColorMeta();
  document.documentElement.addEventListener('turbo:load', syncThemeColorMeta);
})();
