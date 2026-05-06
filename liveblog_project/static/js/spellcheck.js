/**
 * Global spellcheck for textarea and text inputs.
 * Enables browser native spellcheck; lang inherits from document or data-spellcheck-lang.
 * Run on DOMContentLoaded; MutationObserver catches dynamically added elements.
 */
(function () {
  var SPELLCHECK_LANG = 'en'; // fallback when html has no lang

  function getLangFor(el) {
    var ancestor = el.closest('[data-spellcheck-lang]');
    if (ancestor) return ancestor.getAttribute('data-spellcheck-lang');
    return document.documentElement.getAttribute('lang') || SPELLCHECK_LANG;
  }

  function initSpellcheck(el) {
    if (el && !el.hasAttribute('data-spellcheck-init')) {
      el.setAttribute('spellcheck', 'true');
      el.setAttribute('lang', getLangFor(el));
      el.setAttribute('data-spellcheck-init', '1');
    }
  }

  function initAll() {
    var selector = 'textarea, input[type="text"], input[type="search"]';
    document.querySelectorAll(selector).forEach(initSpellcheck);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initAll();
    // Catch dynamically added inputs (e.g. edit form, modals when shown)
    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType === 1) {
            if (node.matches && node.matches('textarea, input[type="text"], input[type="search"]')) {
              initSpellcheck(node);
            }
            if (node.querySelectorAll) {
              node.querySelectorAll('textarea, input[type="text"], input[type="search"]').forEach(initSpellcheck);
            }
          }
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
