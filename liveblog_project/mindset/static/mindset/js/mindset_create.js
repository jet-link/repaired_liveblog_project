/**
 * Mindset — new theme form. CKEditor 5 (Classic) writes back to the underlying
 * <textarea> via a public-ckeditor-ready listener, so a normal POST submit works.
 * We also do a small client-side guard against empty submissions.
 */
(function () {
  'use strict';

  function init() {
    var form = document.getElementById('mindsetThemeForm');
    if (!form) return;

    var ta = form.querySelector('textarea#id_theme_body, textarea[name="body"]');
    if (!ta) return;

    document.addEventListener('public-ckeditor-ready', function (ev) {
      var detail = ev && ev.detail;
      if (!detail || detail.el !== ta) return;
      var editor = detail.editor;
      if (!editor) return;
      editor.model.document.on('change:data', function () {
        try {
          ta.value = editor.getData();
        } catch (e) { /* ignore */ }
      });
      form.addEventListener('submit', function () {
        try {
          ta.value = editor.getData();
        } catch (e) { /* ignore */ }
      });
    });

    form.addEventListener('submit', function (ev) {
      var raw = (ta.value || '').replace(/<[^>]+>/g, ' ').trim();
      if (!raw) {
        ev.preventDefault();
        ta.focus();
        var existing = form.querySelector('.mindset-create__client-error');
        if (existing) existing.remove();
        var hint = document.createElement('div');
        hint.className = 'text-danger small mt-1 mindset-create__client-error';
        hint.textContent = 'Please write your theme body before publishing.';
        ta.parentNode.insertBefore(hint, ta.nextSibling);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  document.addEventListener('turbo:load', init);
})();
