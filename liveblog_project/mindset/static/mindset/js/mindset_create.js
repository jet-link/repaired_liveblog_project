/**
 * Mindset — new theme form. Uses CKEditor 5 (Classic) but with a custom,
 * minimal toolbar (bold / italic / link / undo / redo) — much smaller than
 * the project's shared editor used for posts and comments. We piggy-back on
 * the global ckeditor_main.js loader (which fetches the UMD bundle once),
 * but skip its auto-init by using the .mindset-ckeditor class instead of
 * the generic .ckeditor.
 */
(function () {
  'use strict';

  var TOOLBAR = ['bold', 'italic', 'link', '|', 'undo', 'redo'];

  function waitForClassicEditor(cb, attempts) {
    if (typeof window.ClassicEditor !== 'undefined') {
      cb(window.ClassicEditor);
      return;
    }
    if ((attempts || 0) > 200) return; // ~10s ceiling
    setTimeout(function () { waitForClassicEditor(cb, (attempts || 0) + 1); }, 50);
  }

  function bindEditorWriteback(editor, ta, form) {
    editor.model.document.on('change:data', function () {
      try { ta.value = editor.getData(); } catch (e) { /* ignore */ }
    });
    if (form) {
      form.addEventListener('submit', function () {
        try { ta.value = editor.getData(); } catch (e) { /* ignore */ }
      });
    }
  }

  function initEditor(ta, form) {
    if (!ta || ta.dataset.mindsetCkInit === '1') return;
    if (ta.closest('.ck-editor')) return;
    ta.dataset.mindsetCkInit = '1';

    waitForClassicEditor(function (ClassicEditor) {
      ClassicEditor
        .create(ta, {
          toolbar: TOOLBAR,
          removePlugins: ['MediaEmbed', 'MediaEmbedToolbar', 'AutoMediaEmbed'],
        })
        .then(function (editor) {
          ta._mindsetCkEditor = editor;
          bindEditorWriteback(editor, ta, form);
          var editable = editor.ui && editor.ui.getEditableElement
            ? editor.ui.getEditableElement()
            : null;
          if (editable) {
            editable.setAttribute('spellcheck', 'true');
            var lang = document.documentElement.getAttribute('lang') || 'en';
            editable.setAttribute('lang', lang);
          }
        })
        .catch(function (err) {
          ta.dataset.mindsetCkInit = '';
          console.error('Mindset CKEditor failed to init', err);
        });
    });
  }

  function init() {
    var form = document.getElementById('mindsetThemeForm');
    if (!form) return;

    var ta = form.querySelector('textarea#id_theme_body, textarea[name="body"]');
    if (!ta) return;

    initEditor(ta, form);

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
