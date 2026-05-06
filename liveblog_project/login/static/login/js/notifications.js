(function () {
  'use strict';

  const apiEl = document.getElementById('notificationsPageApi');
  const READ_URL = apiEl?.dataset?.notificationRead || '/profile/notifications/read/';
  const READ_ALL_URL = apiEl?.dataset?.notificationReadAll || '/profile/notifications/read-all/';
  const DELETE_URL = apiEl?.dataset?.notificationDelete || '/profile/notifications/delete/';
  const CHECK_TARGET_URL = apiEl?.dataset?.notificationCheckTarget || '/profile/notifications/check-target/';

  /** Match base.html meta + Django cookie (must match comment_operate / forms that work). */
  function getCSRF() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    const fromMeta = meta && meta.getAttribute('content');
    if (fromMeta) return fromMeta;
    const m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
    if (!m) return '';
    try {
      return decodeURIComponent(m[2]);
    } catch (e) {
      return m[2];
    }
  }

  function post(url, body) {
    const params = new URLSearchParams(body || {});
    params.set('csrfmiddlewaretoken', getCSRF());
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRF(),
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      credentials: 'same-origin',
      body: params.toString()
    });
  }

  function forceCloseModalAndBackdrop() {
    const el = document.getElementById('notificationsDeleteModal');
    try {
      if (el && window.bootstrap && window.bootstrap.Modal) {
        const inst = window.bootstrap.Modal.getInstance(el);
        if (inst) {
          inst.hide();
        } else {
          window.bootstrap.Modal.getOrCreateInstance(el).hide();
        }
      }
    } catch (err) {
      /* ignore */
    }
    document.querySelectorAll('.modal-backdrop').forEach((b) => b.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
  }

  async function notificationDeleteSucceeded(resp) {
    if (!resp || !resp.ok) return false;
    const raw = (await resp.text()).trim();
    if (!raw) return false;
    try {
      const data = JSON.parse(raw);
      return !!(data && data.success === true);
    } catch (e) {
      return false;
    }
  }

  function sendReadToServer(id) {
    if (!id) return;
    const body = new URLSearchParams({
      notification_id: id,
      csrfmiddlewaretoken: getCSRF()
    }).toString();
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/x-www-form-urlencoded' });
      try {
        navigator.sendBeacon(READ_URL, blob);
      } catch (err) {
        /* ignore */
      }
      return;
    }
    fetch(READ_URL, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRF(),
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      credentials: 'same-origin',
      body,
      keepalive: true
    }).catch(() => {});
  }

  const list = document.querySelector('.notifications-list');
  const readAllBtn = document.getElementById('notificationsReadAll');
  const deleteBtn = document.getElementById('notificationsDelete');
  const deleteModalEl = document.getElementById('notificationsDeleteModal');
  const stateEl = document.getElementById('notificationsState');
  const actions = document.getElementById('notificationsActions');
  const emptyState = document.getElementById('notificationsEmpty');
  const legend = document.getElementById('notificationsLegend');
  const legendToggleBtn = document.querySelector('.notification-dropdown-info-btn');
  let unreadCount = parseInt(stateEl?.dataset?.unread || '0', 10);
  let initialSyncDone = false;

  function renderReadBadge(container) {
    const badge = document.createElement('span');
    badge.className = 'notifications-done';
    badge.setAttribute('aria-label', 'Read');
    const icon = document.createElement('i');
    icon.className = 'fa fa-check';
    badge.appendChild(icon);
    container.replaceWith(badge);
  }

  function updateHeaderCount(count) {
    document.querySelectorAll('.notification-btn').forEach(function (btn) {
      if (count > 0) {
        btn.classList.add('has-unread');
      } else {
        btn.classList.remove('has-unread');
      }
    });
    // Badge возле заголовка "Notifications" на странице notifications.html
    const pageBadgeWrap = document.getElementById('notificationsPageBadgeWrap');
    if (!pageBadgeWrap) return;
    let badge = pageBadgeWrap.querySelector('.notifications-count');
    if (count <= 0) {
      if (badge) badge.remove();
    } else {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'notifications-count';
        pageBadgeWrap.appendChild(badge);
      }
      badge.textContent = count >= 10 ? '10+' : String(count);
    }
  }

  function updateReadAllButton() {
    if (!readAllBtn) return;
    if (unreadCount <= 0) {
      readAllBtn.remove();
    }
  }

  function syncUnreadCount() {
    const domCount = document.querySelectorAll('.notification-row[data-is-read="0"]').length;
    const serverCount = stateEl ? parseInt(stateEl.dataset.unread || '0', 10) : 0;
    if (!initialSyncDone) {
      unreadCount = Math.max(domCount, serverCount);
      initialSyncDone = true;
    } else {
      unreadCount = domCount;
    }
    updateHeaderCount(unreadCount);
    updateReadAllButton();
    try {
      localStorage.setItem('notification_unread_count', String(unreadCount));
      localStorage.setItem('notification_count_updated_at', String(Date.now()));
      if (typeof window.updateBellCountFromStorage === 'function') {
        window.updateBellCountFromStorage(unreadCount);
      }
    } catch (err) {}
  }

  function hideActionsIfEmpty() {
    if (!actions) return;
    const remaining = document.querySelectorAll('.notification-row').length;
    if (remaining === 0) {
      actions.classList.add('d-none');
      if (emptyState) emptyState.classList.remove('d-none');
      const wrapper = document.getElementById('notificationsShowMoreWrapper');
      if (wrapper) wrapper.classList.add('d-none');
      if (legend) legend.classList.add('d-none');
      if (legendToggleBtn) legendToggleBtn.classList.add('d-none');
    }
  }

  function initLegendDropdown() {
    if (!legend || !legendToggleBtn) {
      if (legendToggleBtn) legendToggleBtn.classList.add('d-none');
      return;
    }
    legend.classList.remove('is-open');
    legendToggleBtn.classList.remove('is-open');
    legendToggleBtn.setAttribute('aria-expanded', 'false');

    legendToggleBtn.addEventListener('click', () => {
      const isOpen = legend.classList.toggle('is-open');
      legendToggleBtn.classList.toggle('is-open', isOpen);
      legendToggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  function markSeen(id, syncServer = false) {
    if (!id) return;
    if (syncServer) {
      sendReadToServer(id);
    }
    const row = document.querySelector(`.notification-row[data-notification-id="${id}"]`);
    if (row) {
      const wasUnread = row.dataset.isRead !== '1';
      row.classList.add('is-seen');
      row.dataset.isRead = '1';
      row.classList.add('is-read');
      const btn = row.querySelector('.notification-read-btn');
      if (btn) renderReadBadge(btn);
      if (wasUnread) syncUnreadCount();
    }
  }

  function showTargetGoneModal(notifType) {
    const body = document.getElementById('notifTargetGoneBody');
    if (body) {
      const isComment = notifType === 'reply' || notifType === 'comment_like';
      body.textContent = isComment ? 'Comment does not exist' : 'Post does not exist';
    }
    const el = document.getElementById('notifTargetGoneModal');
    if (el && window.bootstrap) {
      bootstrap.Modal.getOrCreateInstance(el).show();
    }
  }

  async function checkTargetAndNavigate(link) {
    const id = link.dataset.notificationId;
    if (!id) { window.location.href = link.href; return; }

    markSeen(id, true);

    const row = link.closest('.notification-row');
    const notifType = row
      ? (row.className.match(/notif-(reply|comment_like|item_like|from_admin)/)?.[1] || 'item_like')
      : 'item_like';

    try {
      const resp = await post(CHECK_TARGET_URL, { notification_id: id });
      if (resp.ok) {
        const data = await resp.json();
        if (data.exists) {
          window.location.href = link.href;
          return;
        }
      }
      showTargetGoneModal(notifType);
    } catch (err) {
      window.location.href = link.href;
    }
  }

  function initSeenMarkers() {
    const rows = document.querySelectorAll('.notification-row');
    rows.forEach(row => {
      const id = row.dataset.notificationId;
      if (!id) return;
      if (row.dataset.isRead === '1') {
        row.classList.add('is-seen', 'is-read');
        const btn = row.querySelector('.notification-read-btn');
        if (btn) renderReadBadge(btn);
      }
    });

    document.querySelectorAll('.notification-target-link').forEach(link => {
      if (link.dataset.seenInit) return;
      link.dataset.seenInit = '1';
      link.addEventListener('click', (e) => {
        e.preventDefault();
        checkTargetAndNavigate(link);
      });
    });
  }

  function initInstantLinkMarking() {
    document.addEventListener('pointerdown', (e) => {
      const link = e.target.closest?.('a.notification-target-link');
      if (!link) return;
      if (e.button !== undefined && e.button !== 0) return;
      const id = link.dataset.notificationId;
      if (id) markSeen(id, true);
    }, true);
  }

  function updateShowMore() {
    const btn = document.getElementById('notificationsShowMoreBtn');
    const rows = Array.from(document.querySelectorAll('.notification-row'));
    if (!btn || !rows.length) return;
    const STEP = 50;
    let shown = Math.min(STEP, rows.length);

    function render() {
      rows.forEach((row, idx) => {
        if (idx < shown) {
          row.classList.remove('listing-hidden');
        } else {
          row.classList.add('listing-hidden');
        }
      });
      if (shown >= rows.length) btn.style.display = 'none';
    }

    render();
    btn.addEventListener('click', () => {
      shown = Math.min(shown + STEP, rows.length);
      render();
    });
  }

  list?.addEventListener('click', (e) => {
    const btn = e.target.closest('.notification-read-btn');
    if (!btn) return;
    const row = btn.closest('.notification-row');
    const id = row?.dataset?.notificationId;
    if (!id) return;

    btn.disabled = true;
    markSeen(id, true);
    hideActionsIfEmpty();
    btn.disabled = false;
  });

  readAllBtn?.addEventListener('click', async () => {
    readAllBtn.disabled = true;
    try {
      const resp = await post(READ_ALL_URL);
      if (!resp.ok) return;
      document.querySelectorAll('.notification-row').forEach(el => {
        el.dataset.isRead = '1';
        el.classList.add('is-read');
        const btn = el.querySelector('.notification-read-btn');
        if (btn) {
          renderReadBadge(btn);
        }
        const id = el.dataset.notificationId;
        if (id) markSeen(id);
      });
      syncUnreadCount();
    } finally {
      readAllBtn.disabled = false;
    }
  });

  deleteBtn?.addEventListener('click', () => {
    const modal = bootstrap.Modal.getOrCreateInstance(deleteModalEl);
    modal.show();
  });

  deleteModalEl?.addEventListener('click', async (e) => {
    const clearAllBtn = e.target.closest('#notificationsDeleteAll');
    const clear5Btn = e.target.closest('#notificationsDeleteLast5');
    if (!clearAllBtn && !clear5Btn) return;
    e.preventDefault();
    e.stopPropagation();

    const isAll = !!clearAllBtn;
    const triggerBtn = isAll ? clearAllBtn : clear5Btn;
    triggerBtn.disabled = true;
    try {
      let resp;
      try {
        resp = await post(DELETE_URL, { mode: isAll ? 'all' : 'last5' });
      } catch (err) {
        return;
      }
      const ok = await notificationDeleteSucceeded(resp);
      if (!ok) return;

      if (isAll) {
        document.querySelectorAll('.notification-row').forEach((el) => el.remove());
        unreadCount = 0;
        updateHeaderCount(unreadCount);
        try {
          localStorage.setItem('notification_unread_count', '0');
          localStorage.setItem('notification_count_updated_at', String(Date.now()));
          if (typeof window.updateBellCountFromStorage === 'function') {
            window.updateBellCountFromStorage();
          }
        } catch (err) {
          /* ignore */
        }
      } else {
        const rows = document.querySelectorAll('.notification-row');
        rows.forEach((el, idx) => {
          if (idx < 5) el.remove();
        });
        syncUnreadCount();
      }
      forceCloseModalAndBackdrop();
      hideActionsIfEmpty();
    } finally {
      triggerBtn.disabled = false;
    }
  });

  updateShowMore();
  initLegendDropdown();
  initInstantLinkMarking();
  initSeenMarkers();
  syncUnreadCount();
  window.addEventListener('pageshow', () => {
    initSeenMarkers();
    syncUnreadCount();
  });
})();
