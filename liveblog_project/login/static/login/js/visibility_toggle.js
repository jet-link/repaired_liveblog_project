(function () {
  'use strict';

  function init() {
    document.querySelectorAll('[data-profile-visibility-toggle][data-public-field]').forEach(function (btn) {
      if (btn.__visBound) return;
      btn.__visBound = true;

      var fieldName = btn.getAttribute('data-public-field');
      var hidden = document.getElementById('id_' + fieldName);
      if (!hidden) return;
      var icon = btn.querySelector('i');

      function visibleToOthers() { return String(hidden.value) === '1'; }

      function syncUi() {
        var show = visibleToOthers();
        if (icon) icon.className = show ? 'fa fa-eye' : 'fa fa-eye-slash';
        btn.setAttribute('aria-pressed', show ? 'false' : 'true');
        btn.setAttribute('aria-label', show ? 'Shown on public profile' : 'Hidden from public profile');
        btn.title = show
          ? 'Shown on public profile. Click to mark hidden from others.'
          : 'Hidden from others. Click to show on public profile.';
      }

      btn.addEventListener('click', function () {
        hidden.value = visibleToOthers() ? '0' : '1';
        syncUi();
      });

      syncUi();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  document.documentElement.addEventListener('turbo:load', init);
})();
