/**
 * Custom category dropdown: keeps native <select> for Django submit/validation.
 */
(function () {
  'use strict';

  function optionLabel(opt) {
    if (!opt) return '';
    var t = (opt.textContent || opt.innerText || '').trim();
    return t;
  }

  function syncTriggerLabel(trigger, select) {
    var opt = select.options[select.selectedIndex];
    trigger.textContent = optionLabel(opt) || '\u2014';
  }

  function closeAllExcept(openWrap) {
    document.querySelectorAll('.category-select-custom.is-open').forEach(function (w) {
      if (w !== openWrap) {
        w.classList.remove('is-open');
        var p = w.querySelector('.category-select-panel');
        var t = w.querySelector('.category-select-trigger');
        if (p) p.hidden = true;
        if (t) t.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function initWrap(wrap) {
    var select = wrap.querySelector('select.custom-select-category');
    if (!select || wrap.getAttribute('data-category-enhanced') === '1') return;
    wrap.setAttribute('data-category-enhanced', '1');
    select.classList.add('category-select-native');

    var inner = document.createElement('div');
    inner.className = 'category-select-inner';
    wrap.insertBefore(inner, select);

    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'category-select-trigger custom-select-category';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.id = 'category-select-trigger-' + (select.id || 'cat');
    syncTriggerLabel(trigger, select);

    var panel = document.createElement('div');
    panel.className = 'category-select-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'presentation');

    var ul = document.createElement('ul');
    ul.className = 'category-select-options';
    ul.setAttribute('role', 'listbox');
    ul.setAttribute('aria-labelledby', trigger.id);

    function rebuildOptions() {
      ul.innerHTML = '';
      for (var i = 0; i < select.options.length; i++) {
        (function (idx) {
          var opt = select.options[idx];
          var li = document.createElement('li');
          li.setAttribute('role', 'option');
          li.className = 'category-select-option';
          li.dataset.value = opt.value;
          if (opt.selected) li.setAttribute('aria-selected', 'true');
          else li.setAttribute('aria-selected', 'false');
          li.textContent = optionLabel(opt) || '\u2014';
          li.addEventListener('mousedown', function (e) {
            e.preventDefault();
          });
          li.addEventListener('click', function () {
            select.selectedIndex = idx;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            syncTriggerLabel(trigger, select);
            ul.querySelectorAll('[role="option"]').forEach(function (el, j) {
              el.setAttribute('aria-selected', j === idx ? 'true' : 'false');
            });
            panel.hidden = true;
            wrap.classList.remove('is-open');
            trigger.setAttribute('aria-expanded', 'false');
          });
          ul.appendChild(li);
        })(i);
      }
    }

    rebuildOptions();
    select.addEventListener('change', function () {
      syncTriggerLabel(trigger, select);
      rebuildOptions();
    });

    panel.appendChild(ul);
    inner.appendChild(trigger);
    inner.appendChild(panel);

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = panel.hidden;
      closeAllExcept(wrap);
      if (open) {
        panel.hidden = false;
        wrap.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
      } else {
        panel.hidden = true;
        wrap.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('click', function () {
      if (!panel.hidden) {
        panel.hidden = true;
        wrap.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && wrap.classList.contains('is-open')) {
        panel.hidden = true;
        wrap.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.category-select-custom').forEach(initWrap);
  });
})();
