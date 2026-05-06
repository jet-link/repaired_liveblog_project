/**
 * Custom admin toolbar: auto-submit on change for select filters.
 * (Not named filters.js — that path is Django's changelist filter state script.)
 */
(function() {
  'use strict';

  function bindAdminToolbarSelectFilters(scope) {
    var root = scope || document;
    root.querySelectorAll('.admin-toolbar select:not([data-admin-toolbar-filter-bound])').forEach(function(select) {
      select.setAttribute('data-admin-toolbar-filter-bound', '1');
      select.addEventListener('change', function() {
        var form = select.closest('form');
        if (form) form.submit();
      });
    });
  }

  window.adminBindToolbarSelectFilters = bindAdminToolbarSelectFilters;

  bindAdminToolbarSelectFilters(document);

})();
