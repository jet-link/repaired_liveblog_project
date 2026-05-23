/**
 * Mindset — new theme form. Uses CKEditor 5 (Classic) with a compact toolbar
 * (bold / italic / link / lists / block quote / undo / redo). Loads via the
 * shared ckeditor_main.js bundle; `.mindset-ckeditor` skips generic `.ckeditor`
 * auto-init.
 */
(function () {
  'use strict';

  var TOOLBAR = [
    'bold',
    'italic',
    'link',
    '|',
    'bulletedList',
    'numberedList',
    '|',
    'blockQuote',
    '|',
    'undo',
    'redo',
  ];

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

  var IMAGE_MIME_ALLOWED = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];

  function humanFileSize(size) {
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    return (size / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function makeThemePreviewBlock(file) {
    var wrap = document.createElement('div');
    wrap.className = 'image-preview-item existing-image position-relative text-center';

    var img = document.createElement('img');
    var reader = new FileReader();
    reader.onload = function (e) { img.src = e.target.result; };
    reader.readAsDataURL(file);

    var meta = document.createElement('div');
    meta.style.marginTop = '8px';
    var nameNode = document.createElement('small');
    nameNode.textContent = file.name;
    nameNode.style.display = 'block';
    var sizeNode = document.createElement('small');
    sizeNode.className = 'text-muted d-block';
    sizeNode.textContent = humanFileSize(file.size);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-danger btn-delete-image';
    btn.dataset.action = 'remove-temp';
    btn.innerHTML = '<i class="fa fa-times"></i>';

    wrap.appendChild(img);
    meta.appendChild(nameNode);
    meta.appendChild(sizeNode);
    wrap.appendChild(meta);
    wrap.appendChild(btn);
    return wrap;
  }

  /**
   * Wire the multi-image input on the New Theme page: client-side cap, MIME
   * filter, and thumbnail strip identical to the post-create page.
   */
  function initThemeImages(form) {
    var input = form.querySelector('input.mindset-images-file-input');
    if (!input) return;
    var max = parseInt(input.dataset.maxFiles || '3', 10);
    if (!isFinite(max) || max < 1) max = 3;
    var previewBox = form.querySelector('[data-mindset-images-preview]');
    var helpNode = form.querySelector('#mindsetImagesHelp');
    var originalHelp = helpNode ? helpNode.textContent : '';

    function setHelp(text, warn) {
      if (!helpNode) return;
      helpNode.textContent = text;
      helpNode.classList.toggle('text-danger', !!warn);
    }

    function rerender() {
      if (!previewBox) return;
      previewBox.innerHTML = '';
      Array.from(input.files || []).forEach(function (file) {
        previewBox.appendChild(makeThemePreviewBlock(file));
      });
    }

    function clampFiles(files) {
      var kept = files.filter(function (f) {
        return IMAGE_MIME_ALLOWED.indexOf((f.type || '').toLowerCase()) !== -1;
      });
      var dropped = files.length - kept.length;
      if (kept.length > max) {
        kept = kept.slice(0, max);
        setHelp('You can attach up to ' + max + ' images. Extra files were not added.', true);
      } else if (dropped > 0) {
        setHelp('Removed ' + dropped + ' unsupported file(s).', true);
      } else {
        setHelp(originalHelp, false);
      }
      var dt = new DataTransfer();
      kept.forEach(function (f) { dt.items.add(f); });
      input.files = dt.files;
      rerender();
    }

    input.addEventListener('change', function () {
      clampFiles(Array.from(input.files || []));
    });

    if (previewBox) {
      previewBox.addEventListener('click', function (ev) {
        var btn = ev.target.closest('button.btn-delete-image');
        if (!btn) return;
        ev.preventDefault();
        var item = btn.closest('.image-preview-item');
        if (!item) return;
        var idx = Array.from(previewBox.querySelectorAll('.image-preview-item')).indexOf(item);
        if (idx < 0) return;
        var dt = new DataTransfer();
        Array.from(input.files || []).forEach(function (f, i) {
          if (i !== idx) dt.items.add(f);
        });
        input.files = dt.files;
        rerender();
        setHelp(originalHelp, false);
      });
    }
  }

  function init() {
    var form = document.getElementById('mindsetThemeForm');
    if (!form) return;

    var ta = form.querySelector('textarea#id_theme_body, textarea[name="body"]');
    if (!ta) return;

    initEditor(ta, form);
    initThemeImages(form);

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
