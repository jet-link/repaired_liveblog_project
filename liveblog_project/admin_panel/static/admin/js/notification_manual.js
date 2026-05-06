(function () {
  'use strict';

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) return meta.getAttribute('content');
    if (typeof window.ADMIN_CSRF_TOKEN === 'string' && window.ADMIN_CSRF_TOKEN) {
      return window.ADMIN_CSRF_TOKEN;
    }
    return '';
  }

  var searchTimer;
  var activeIdx = -1;
  var lastResults = [];
  /** Button that opened "View notification" — return focus on close to avoid aria-hidden on an ancestor of the focused control. */
  var lastViewNotifOpener = null;

  function openModal(el) {
    if (!el) return;
    el.removeAttribute('hidden');
    el.classList.add('is-open');
    el.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal(el) {
    if (!el) return;
    // Move focus out before aria-hidden, or the browser warns (focused node inside "hidden" subtree)
    if (document.activeElement && el.contains(document.activeElement) && document.activeElement.blur) {
      document.activeElement.blur();
    }
    el.classList.remove('is-open');
    el.setAttribute('aria-hidden', 'true');
    el.setAttribute('hidden', '');
    document.body.style.overflow = '';
  }

  function closeViewNotifModal() {
    var viewModal = document.getElementById('adminNotifViewModal');
    if (!viewModal) return;
    if (document.activeElement && viewModal.contains(document.activeElement)) {
      if (lastViewNotifOpener && document.body.contains(lastViewNotifOpener) && lastViewNotifOpener.focus) {
        lastViewNotifOpener.focus();
      } else if (document.activeElement.blur) {
        document.activeElement.blur();
      }
    }
    closeModal(viewModal);
  }

  function bindViewNotifModal() {
    if (window.__adminNotifViewDelegate) return;
    window.__adminNotifViewDelegate = true;

    document.addEventListener('click', function (e) {
      var viewModal = document.getElementById('adminNotifViewModal');
      if (!viewModal) return;
      if (e.target && e.target.id === 'adminNotifViewModalBackdrop') {
        closeViewNotifModal();
        return;
      }
      if (e.target && (e.target.id === 'adminNotifViewClose' || (e.target.closest && e.target.closest('#adminNotifViewClose')))) {
        e.preventDefault();
        closeViewNotifModal();
        return;
      }
      var btn = e.target && e.target.closest && e.target.closest('.js-admin-notif-view-open');
      if (!btn) return;
      e.preventDefault();
      var url = btn.getAttribute('data-detail-url');
      if (!url) return;
      lastViewNotifOpener = btn;
      var themeEl = document.getElementById('adminNotifViewTheme');
      var bodyEl = document.getElementById('adminNotifViewBody');
      var recipientEl = document.getElementById('adminNotifViewRecipient');
      if (themeEl) themeEl.textContent = '…';
      if (bodyEl) bodyEl.textContent = '…';
      if (recipientEl) recipientEl.textContent = '…';
      openModal(viewModal);
      fetch(url, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
        credentials: 'same-origin',
      })
        .then(function (r) {
          if (!r.ok) throw new Error();
          return r.json();
        })
        .then(function (data) {
          if (themeEl) themeEl.textContent = (data && data.theme) || '—';
          if (bodyEl) bodyEl.textContent = (data && data.body) || '';
          if (recipientEl) recipientEl.textContent = (data && data.recipient) || '';
        })
        .catch(function () {
          if (themeEl) themeEl.textContent = '';
          if (bodyEl) bodyEl.textContent = 'Could not load notification.';
          if (recipientEl) recipientEl.textContent = '';
        });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var viewModal = document.getElementById('adminNotifViewModal');
      if (viewModal && viewModal.classList.contains('is-open')) {
        closeViewNotifModal();
      }
    });
  }

  function closeList(input, list) {
    list.setAttribute('aria-hidden', 'true');
    list.setAttribute('hidden', '');
    list.innerHTML = '';
    input.setAttribute('aria-expanded', 'false');
    activeIdx = -1;
    lastResults = [];
  }

  function renderList(list, results, onPick) {
    list.innerHTML = '';
    lastResults = results;
    results.forEach(function (u, i) {
      var li = document.createElement('li');
      li.setAttribute('role', 'presentation');
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'admin-user-combobox__item';
      btn.setAttribute('role', 'option');
      btn.setAttribute('id', 'manual_user_opt_' + u.id);
      btn.textContent = u.username;
      btn.addEventListener('click', function () {
        onPick(u);
      });
      li.appendChild(btn);
      list.appendChild(li);
    });
    if (results.length) {
      list.removeAttribute('hidden');
      list.setAttribute('aria-hidden', 'false');
    } else {
      list.setAttribute('hidden', '');
    }
  }

  function runSearch(form, q, onPick) {
    var url = form.getAttribute('data-search-url');
    if (!url) return;
    var list = document.getElementById('id_manual_user_list');
    var input = document.getElementById('id_manual_user');
    if (q.length < 1) {
      closeList(input, list);
      return;
    }
    var params = new URLSearchParams({ q: q });
    fetch(url + '?' + params.toString(), {
      method: 'GET',
      headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var res = (data && data.results) || [];
        renderList(list, res, onPick);
        input.setAttribute('aria-expanded', res.length ? 'true' : 'false');
        activeIdx = -1;
      })
      .catch(function () {
        closeList(input, list);
      });
  }

  function pickUser(u, form) {
    var idInput = document.getElementById('id_manual_user_id');
    var textInput = document.getElementById('id_manual_user');
    if (idInput) idInput.value = String(u.id);
    if (textInput) {
      textInput.value = u.username;
      textInput.setAttribute('aria-activedescendant', '');
    }
    var list = document.getElementById('id_manual_user_list');
    if (list) {
      list.innerHTML = '';
      list.setAttribute('hidden', '');
      list.setAttribute('aria-hidden', 'true');
    }
  }

  function bind() {
    var form = document.getElementById('adminManualNotifForm');
    var modal = document.getElementById('adminManualNotifModal');
    var openBtn = document.getElementById('adminManualNotifOpen');
    var cancel = document.getElementById('adminManualNotifCancel');
    if (!form || !modal) return;
    if (form.dataset.bound === '1') return;
    form.dataset.bound = '1';

    var input = document.getElementById('id_manual_user');
    var list = document.getElementById('id_manual_user_list');
    var idInput = document.getElementById('id_manual_user_id');

    function onPick(u) {
      pickUser(u, form);
    }

    function showErr(msg) {
      var el = document.getElementById('adminManualNotifErrors');
      if (!el) return;
      if (msg) {
        el.textContent = msg;
        el.style.display = 'block';
      } else {
        el.textContent = '';
        el.style.display = 'none';
      }
    }

    function resetForm() {
      form.reset();
      if (idInput) idInput.value = '';
      if (list) {
        list.innerHTML = '';
        list.setAttribute('hidden', '');
        list.setAttribute('aria-hidden', 'true');
      }
      showErr('');
    }

    if (openBtn) {
      openBtn.addEventListener('click', function (e) {
        e.preventDefault();
        resetForm();
        openModal(modal);
        setTimeout(function () {
          var t = document.getElementById('id_manual_theme');
          if (t) t.focus();
        }, 50);
      });
    }

    if (cancel) {
      cancel.addEventListener('click', function (e) {
        e.preventDefault();
        closeModal(modal);
        resetForm();
      });
    }

    document.getElementById('adminManualNotifModalBackdrop')?.addEventListener('click', function () {
      closeModal(modal);
      resetForm();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal && modal.classList.contains('is-open')) {
        closeModal(modal);
        resetForm();
      }
    });

    input.addEventListener('input', function () {
      if (idInput) idInput.value = '';
      var q = (input.value || '').trim();
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        runSearch(form, q, onPick);
      }, 300);
    });

    input.addEventListener('keydown', function (e) {
      if (!list || list.getAttribute('aria-hidden') === 'true') return;
      var items = list.querySelectorAll('.admin-user-combobox__item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        items.forEach(function (b, j) {
          b.setAttribute('aria-selected', j === activeIdx ? 'true' : 'false');
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        items.forEach(function (b, j) {
          b.setAttribute('aria-selected', j === activeIdx ? 'true' : 'false');
        });
      } else if (e.key === 'Enter' && activeIdx >= 0 && lastResults[activeIdx]) {
        e.preventDefault();
        onPick(lastResults[activeIdx]);
      }
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var uid = (idInput && idInput.value) || '';
      var body = (document.getElementById('id_manual_body') && document.getElementById('id_manual_body').value) || '';
      var theme = (document.getElementById('id_manual_theme') && document.getElementById('id_manual_theme').value) || '';
      if (!uid) {
        showErr('Select a user from the search list.');
        return;
      }
      if (!body.trim()) {
        showErr('Notification body is required.');
        return;
      }
      var sendUrl = form.getAttribute('data-send-url');
      var sendBtn = document.getElementById('adminManualNotifSend');
      if (sendBtn) sendBtn.disabled = true;
      showErr('');
      fetch(sendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ user_id: parseInt(uid, 10), theme: theme, body: body }),
      })
        .then(function (r) {
          return r
            .json()
            .then(function (j) {
              return { ok: r.ok, j: j };
            })
            .catch(function () {
              return { ok: r.ok, j: { error: r.status + ' ' + r.statusText } };
            });
        })
        .then(function (o) {
          if (o.ok && o.j && o.j.success) {
            closeModal(modal);
            resetForm();
            window.location.reload();
            return;
          }
          showErr((o.j && o.j.error) || 'Failed to send.');
        })
        .catch(function () {
          showErr('Request failed.');
        })
        .finally(function () {
          if (sendBtn) sendBtn.disabled = false;
        });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      bind();
      bindViewNotifModal();
    });
  } else {
    bind();
    bindViewNotifModal();
  }
  document.addEventListener('turbo:load', function () {
    bind();
    bindViewNotifModal();
  });
})();
