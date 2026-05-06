/**
 * Public site CKEditor 5 (Classic). Loads the UMD build exactly once per window
 * to avoid CKEditorError: ckeditor-duplicated-modules when scripts re-run (e.g. Turbo).
 */
(function () {
	'use strict';

	var CLASSIC_SRC = 'https://cdn.ckeditor.com/ckeditor5/39.0.1/classic/ckeditor.js';
	var SCRIPT_ID = 'ckeditor5-public-classic-umd';

	function initEditors() {
		if (typeof ClassicEditor === 'undefined') return;

		document.querySelectorAll('.ckeditor').forEach(function (el) {
			if (!el || el.nodeType !== 1) return;
			if (el.classList.contains('ck-hidden')) return;
			if (el.closest('.ck-editor')) return;
			if (el.getAttribute('data-ck-initializing') === '1') return;

			el.setAttribute('data-ck-initializing', '1');
			ClassicEditor
				.create(el, {
					toolbar: [
						'heading',
						'|',
						'bold',
						'italic',
						'link',
						'bulletedList',
						'numberedList',
						'|',
						'blockQuote',
						'undo',
						'redo'
					]
				})
				.then(function (editor) {
					el.removeAttribute('data-ck-initializing');
					el._publicCKEditorInstance = editor;
					try {
						el.dispatchEvent(
							new CustomEvent('public-ckeditor-ready', {
								bubbles: true,
								detail: { el: el, editor: editor }
							})
						);
					} catch (e) { /* ignore */ }
					var textareaId = el.id;
					var editable = editor.ui && editor.ui.getEditableElement
						? editor.ui.getEditableElement()
						: (editor.ui && editor.ui.view ? editor.ui.view.editableElement : null);
					if (editable) {
						editable.setAttribute('spellcheck', 'true');
						var langEl = editable.closest('[data-spellcheck-lang]');
						var lang = langEl
							? langEl.getAttribute('data-spellcheck-lang')
							: (document.documentElement.getAttribute('lang') || 'ru');
						editable.setAttribute('lang', lang);
					}
					if (!textareaId) return;
					var attempts = 0;
					var tryFix = function () {
						var editEl = editor.ui && editor.ui.getEditableElement
							? editor.ui.getEditableElement()
							: (editor.ui && editor.ui.view ? editor.ui.view.editableElement : null);
						var editorRoot = editEl
							? editEl.closest('.ck-editor')
							: (el.parentElement && el.parentElement.querySelector
								? el.parentElement.querySelector('.ck-editor')
								: null);
						var label = editorRoot ? editorRoot.querySelector('.ck-voice-label') : null;
						if (label) {
							label.setAttribute('for', textareaId);
						} else if (attempts++ < 50) {
							requestAnimationFrame(tryFix);
						}
					};
					tryFix();
				})
				.catch(function (error) {
					el.removeAttribute('data-ck-initializing');
					console.error(error);
				});
		});
	}

	function ensureClassicEditor(done) {
		if (typeof ClassicEditor !== 'undefined') {
			done();
			return;
		}
		var existing = document.getElementById(SCRIPT_ID);
		if (existing) {
			if (existing.getAttribute('data-ck-loaded') === '1') {
				done();
			} else {
				existing.addEventListener('load', done, { once: true });
				existing.addEventListener('error', function () {
					console.error('CKEditor classic build failed to load');
				}, { once: true });
			}
			return;
		}
		var s = document.createElement('script');
		s.id = SCRIPT_ID;
		s.async = true;
		s.src = CLASSIC_SRC;
		s.setAttribute('crossorigin', 'anonymous');
		s.addEventListener('load', function () {
			s.setAttribute('data-ck-loaded', '1');
			done();
		});
		s.addEventListener('error', function () {
			console.error('CKEditor classic build failed to load');
		}, { once: true });
		document.head.appendChild(s);
	}

	function boot() {
		ensureClassicEditor(initEditors);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', boot);
	} else {
		boot();
	}

	document.addEventListener('turbo:load', boot);
})();
