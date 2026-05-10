/**
 * Mindset feed JS.
 *
 * Hybrid live updates:
 *   - Author of an action sees an instant DOM update because the API responds with
 *     rendered HTML and fresh counters.
 *   - Other tabs poll /mindset/api/themes/state/ and /mindset/api/sidebar/ to get
 *     refreshed counters and any new replies (per-theme, since_id-based).
 */
(function () {
  'use strict';

  var ROOT_SELECTOR = '[data-mindset-feed]';
  var THEME_POLL_MS = 7000;
  var SIDEBAR_POLL_MS = 30000;
  var REPLY_COOLDOWN_SEC = 30;
  var REPLY_COOLDOWN_KEY_PREFIX = 'mindset_reply_cooldown_until_';

  function humanize(n) {
    n = Number(n);
    if (!isFinite(n) || isNaN(n)) return '0';
    if (n < 1000) return String(n);
    var tiers = [
      [1e9, 'B'],
      [1e6, 'M'],
      [1e3, 'K'],
    ];
    for (var i = 0; i < tiers.length; i++) {
      var threshold = tiers[i][0];
      var suffix = tiers[i][1];
      if (n >= threshold) {
        var val = n / threshold;
        if (val >= 10) return Math.floor(val) + suffix;
        var truncated = Math.floor(val * 10) / 10;
        return truncated.toFixed(1).replace(/\.0$/, '') + suffix;
      }
    }
    return String(n);
  }

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function fetchJson(url, opts) {
    opts = opts || {};
    opts.credentials = 'same-origin';
    opts.headers = Object.assign(
      { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      opts.headers || {}
    );
    return fetch(url, opts).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function postForm(url, formData) {
    var fd = formData || new FormData();
    if (!fd.get('csrfmiddlewaretoken')) {
      fd.append('csrfmiddlewaretoken', getCsrf());
    }
    return fetchJson(url, { method: 'POST', body: fd });
  }

  function setCounter(scope, kind, value) {
    if (!scope || value === undefined || value === null) return;
    var el = scope.querySelector('[data-counter="' + kind + '"] [data-counter-val]');
    if (el) {
      el.textContent = typeof value === 'string' ? value : humanize(value);
    }
  }

  function paintLikeButton(btn, liked) {
    if (!btn) return;
    btn.classList.toggle('is-active', !!liked);
    btn.setAttribute('aria-pressed', liked ? 'true' : 'false');
    var heart = btn.querySelector('i.fa');
    if (heart) heart.className = 'fa ' + (liked ? 'fa-heart' : 'fa-heart-o');
    var label = btn.querySelector('span');
    if (label) label.textContent = liked ? 'Liked' : 'Like';
  }

  function paintRepostButton(btn, reposted) {
    if (!btn) return;
    btn.classList.toggle('is-active', !!reposted);
    btn.setAttribute('aria-pressed', reposted ? 'true' : 'false');
    var label = btn.querySelector('span');
    if (label) label.textContent = reposted ? 'Reposted' : 'Repost';
  }

  /**
   * Apply state to a theme card. ``opts.skip`` is a Set of buttons to skip
   * ("like" or "repost") — used to keep the button the user just clicked
   * authoritative when the OTHER button's response arrives.
   */
  function applyThemeState(state, opts) {
    if (!state || !state.id) return;
    opts = opts || {};
    var card = document.querySelector('[data-mindset-theme="' + state.id + '"]');
    if (!card) return;
    setCounter(card, 'replies', state.replies_count_human != null ? state.replies_count_human : state.replies_count);
    setCounter(card, 'likes', state.likes_count_human != null ? state.likes_count_human : state.likes_count);
    setCounter(card, 'reposts', state.reposts_count_human != null ? state.reposts_count_human : state.reposts_count);

    if (!opts.skipLike && state.user_liked !== undefined) {
      paintLikeButton(card.querySelector('[data-action="like"]'), state.user_liked);
    }
    if (!opts.skipRepost && state.user_reposted !== undefined) {
      paintRepostButton(card.querySelector('[data-action="repost"]'), state.user_reposted);
    }
  }

  function applyReplyState(state, opts) {
    if (!state || !state.id) return;
    opts = opts || {};
    var node = document.querySelector('[data-mindset-reply="' + state.id + '"]');
    if (!node) return;
    setCounter(node, 'replies', state.replies_count_human != null ? state.replies_count_human : state.replies_count);
    setCounter(node, 'likes', state.likes_count_human != null ? state.likes_count_human : state.likes_count);
    setCounter(node, 'reposts', state.reposts_count_human != null ? state.reposts_count_human : state.reposts_count);

    if (!opts.skipLike && state.user_liked !== undefined) {
      paintLikeButton(node.querySelector('[data-action="reply-like"]'), state.user_liked);
    }
    if (!opts.skipRepost && state.user_reposted !== undefined) {
      paintRepostButton(node.querySelector('[data-action="reply-repost"]'), state.user_reposted);
    }
  }

  function findVisibleThemeIds() {
    var ids = [];
    document.querySelectorAll('[data-mindset-theme]').forEach(function (el) {
      var id = el.getAttribute('data-mindset-theme');
      if (id) ids.push(id);
    });
    return ids;
  }

  function maxReplyIdInTheme(themeId) {
    var maxId = 0;
    document.querySelectorAll('[data-mindset-replies="' + themeId + '"] [data-mindset-reply]').forEach(function (el) {
      var pid = el.getAttribute('data-mindset-reply');
      var n = parseInt(pid, 10);
      if (!isNaN(n) && n > maxId) maxId = n;
    });
    return maxId;
  }

  function appendReplyHtml(themeId, html) {
    var container = document.querySelector('[data-mindset-replies="' + themeId + '"]');
    if (!container) return;
    container.insertAdjacentHTML('afterbegin', html);
  }

  // ---- auto-grow textarea (mirror of comment_operate behaviour) -----------

  function autoResizeTextarea(ta) {
    if (!ta) return;
    var cs = window.getComputedStyle(ta);
    var minH = parseFloat(cs.minHeight) || 0;
    ta.style.height = 'auto';
    var next = Math.max(minH, ta.scrollHeight);
    ta.style.height = next + 'px';
  }

  function bindAutoGrow(ta) {
    if (!ta || ta.dataset.mindsetAutoGrowBound === '1') return;
    ta.dataset.mindsetAutoGrowBound = '1';
    autoResizeTextarea(ta);
    ta.addEventListener('input', function () { autoResizeTextarea(ta); });
    ta.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      requestAnimationFrame(function () { autoResizeTextarea(ta); });
    });
  }

  // ---- reply cooldown (per user + theme, 30s) ------------------------------

  function getUserId(root) {
    var r = root || document.querySelector(ROOT_SELECTOR);
    return r ? (r.getAttribute('data-user-id') || '') : '';
  }

  function replyCooldownStorageKey(themeId, userId) {
    if (!themeId || !userId) return null;
    return REPLY_COOLDOWN_KEY_PREFIX + userId + '_' + themeId;
  }

  function getReplyCooldownRemaining(themeId, userId) {
    var key = replyCooldownStorageKey(themeId, userId);
    if (!key) return 0;
    var until = Number(localStorage.getItem(key) || 0);
    var diff = Math.ceil((until - Date.now()) / 1000);
    return diff > 0 ? diff : 0;
  }

  function paintReplyButtonCooldown(btn, themeId, userId) {
    if (!btn || !themeId) return;
    if (!btn.dataset.originalReplyText) {
      var labelSpan = btn.querySelector('span');
      btn.dataset.originalReplyText =
        (labelSpan && labelSpan.textContent.trim()) || 'Reply';
    }
    var original = btn.dataset.originalReplyText || 'Reply';
    var remaining = getReplyCooldownRemaining(themeId, userId);

    var labelEl = btn.querySelector('span');

    if (remaining > 0) {
      btn.disabled = true;
      btn.classList.add('is-blocked');
      btn.setAttribute('aria-disabled', 'true');
      if (labelEl) labelEl.textContent = 'Wait ' + remaining + 's';

      if (!btn.__replyCooldownTimer) {
        btn.__replyCooldownTimer = setInterval(function () {
          var left = getReplyCooldownRemaining(themeId, userId);
          if (left <= 0) {
            clearInterval(btn.__replyCooldownTimer);
            btn.__replyCooldownTimer = null;
            var key = replyCooldownStorageKey(themeId, userId);
            if (key) localStorage.removeItem(key);
            btn.disabled = false;
            btn.classList.remove('is-blocked');
            btn.removeAttribute('aria-disabled');
            if (labelEl) labelEl.textContent = original;
            return;
          }
          if (labelEl) labelEl.textContent = 'Wait ' + left + 's';
        }, 1000);
      }
      return;
    }

    if (btn.__replyCooldownTimer) {
      clearInterval(btn.__replyCooldownTimer);
      btn.__replyCooldownTimer = null;
    }
    btn.disabled = false;
    btn.classList.remove('is-blocked');
    btn.removeAttribute('aria-disabled');
    if (labelEl) labelEl.textContent = original;
  }

  function startReplyCooldown(themeId, userId, seconds) {
    if (!themeId || !userId) return;
    var key = replyCooldownStorageKey(themeId, userId);
    if (!key) return;
    var sec = Number(seconds) || REPLY_COOLDOWN_SEC;
    localStorage.setItem(key, String(Date.now() + sec * 1000));
    document
      .querySelectorAll('[data-action="reply"][data-theme-id="' + themeId + '"]')
      .forEach(function (btn) { paintReplyButtonCooldown(btn, themeId, userId); });
  }

  function initAllReplyCooldowns(root) {
    var userId = getUserId(root);
    if (!userId) return;
    document
      .querySelectorAll('[data-action="reply"][data-theme-id]')
      .forEach(function (btn) {
        var tid = btn.getAttribute('data-theme-id');
        if (tid) paintReplyButtonCooldown(btn, tid, userId);
      });
  }

  function parseCooldownSeconds(message) {
    if (!message) return null;
    var match = String(message).match(/(\d+)\s*s/);
    if (!match) return null;
    var n = parseInt(match[1], 10);
    return isNaN(n) ? null : n;
  }

  // ---- action handlers (instant for the actor) -----------------------------

  function bindRoot(root) {
    if (root.__mindsetBound) return;
    root.__mindsetBound = true;
    var auth = root.getAttribute('data-user-authenticated') === '1';

    root.addEventListener('click', function (ev) {
      // Cancel buttons (reply form)
      var cancelBtn = ev.target.closest('[data-mindset-reply-cancel]');
      if (cancelBtn) {
        var fcancel = cancelBtn.closest('form');
        if (fcancel) fcancel.hidden = true;
        return;
      }

      var btn = ev.target.closest('[data-action]');
      if (!btn) return;
      var action = btn.getAttribute('data-action');
      var card = btn.closest('[data-mindset-theme]');

      if (action === 'reply') {
        if (!card) return;
        var themeIdAttr = btn.getAttribute('data-theme-id') || card.getAttribute('data-mindset-theme');
        var userIdRoot = getUserId(root);
        if (themeIdAttr && userIdRoot && getReplyCooldownRemaining(themeIdAttr, userIdRoot) > 0) {
          paintReplyButtonCooldown(btn, themeIdAttr, userIdRoot);
          return;
        }
        var form = card.querySelector(':scope > [data-mindset-reply-form]');
        if (form) {
          form.hidden = !form.hidden;
          btn.setAttribute('aria-expanded', form.hidden ? 'false' : 'true');
          if (!form.hidden) {
            var ta = form.querySelector('textarea');
            if (ta) {
              bindAutoGrow(ta);
              autoResizeTextarea(ta);
              ta.focus();
            }
          }
        }
        return;
      }

      if (!auth) return;

      if (action === 'like' || action === 'repost') {
        var url = btn.getAttribute('data-url');
        if (!url || btn.disabled) return;
        btn.disabled = true;
        postForm(url).then(function (resp) {
          btn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok && resp.data.theme) {
            applyThemeState(resp.data.theme);
          } else if (resp.data && resp.data.error) {
            console.warn('Mindset:', resp.data.error);
          }
        }).catch(function () { btn.disabled = false; });
        return;
      }

      if (action === 'reply-like' || action === 'reply-repost') {
        var rurl = btn.getAttribute('data-url');
        if (!rurl || btn.disabled) return;
        btn.disabled = true;
        postForm(rurl).then(function (resp) {
          btn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok && resp.data.reply) {
            applyReplyState(resp.data.reply);
          } else if (resp.data && resp.data.error) {
            console.warn('Mindset:', resp.data.error);
          }
        }).catch(function () { btn.disabled = false; });
        return;
      }
    });

    // Submit reply form
    root.addEventListener('submit', function (ev) {
      var form = ev.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (form.hasAttribute('data-mindset-reply-form')) {
        ev.preventDefault();
        submitReplyForm(form);
      }
    });
  }

  // ---- Delete confirmation modal ------------------------------------------

  function bindDeleteModal() {
    var modal = document.getElementById('mindsetConfirmDeleteModal');
    if (!modal || modal.__mindsetBound) return;
    modal.__mindsetBound = true;

    var titleEl = modal.querySelector('.modal-title');
    var bodyEl = modal.querySelector('[data-mindset-delete-modal-body]');
    var confirmBtn = modal.querySelector('#mindsetConfirmDeleteBtn');

    var ctx = { kind: null, id: null, url: null };

    modal.addEventListener('show.bs.modal', function (ev) {
      var trigger = ev.relatedTarget;
      if (!trigger) return;
      ctx.kind = trigger.getAttribute('data-mindset-delete-kind');
      ctx.id = trigger.getAttribute('data-mindset-delete-id');
      ctx.url = trigger.getAttribute('data-mindset-delete-url');

      if (ctx.kind === 'theme') {
        if (titleEl) titleEl.textContent = 'Remove theme';
        if (bodyEl) bodyEl.innerHTML = 'Are you sure you want to remove this theme? <span class="text-danger fw-semibold">All replies will be removed too.</span>';
      } else {
        if (titleEl) titleEl.textContent = 'Remove reply';
        if (bodyEl) bodyEl.textContent = 'Are you sure you want to remove this reply?';
      }
    });

    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        if (!ctx.url) return;
        confirmBtn.disabled = true;
        postForm(ctx.url).then(function (resp) {
          confirmBtn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok) {
            if (ctx.kind === 'theme') {
              var card = document.querySelector('[data-mindset-theme="' + ctx.id + '"]');
              if (card) card.remove();
            } else {
              var node = document.querySelector('[data-mindset-reply="' + ctx.id + '"]');
              if (node) node.remove();
              if (resp.data.theme) applyThemeState(resp.data.theme);
            }
            refreshSidebar();
            try {
              var inst = window.bootstrap && window.bootstrap.Modal.getInstance(modal);
              if (inst) inst.hide();
            } catch (e) { /* ignore */ }
          } else {
            alert((resp.data && resp.data.error) || 'Could not delete.');
          }
        }).catch(function () {
          confirmBtn.disabled = false;
          alert('Network error.');
        });
      });
    }
  }

  function submitReplyForm(form) {
    var errBox = form.querySelector('[data-mindset-reply-error]');
    if (errBox) { errBox.hidden = true; errBox.textContent = ''; }
    var submitBtn = form.querySelector('button[type="submit"]');
    var ta = form.querySelector('textarea[name="body"]');
    if (!ta || !ta.value.trim()) {
      if (errBox) { errBox.textContent = 'Reply cannot be empty.'; errBox.hidden = false; }
      return;
    }
    if (submitBtn) submitBtn.disabled = true;

    var fd = new FormData(form);
    var themeIdForm = form.getAttribute('data-theme-id');
    var userIdForm = getUserId();
    postForm(form.action, fd).then(function (resp) {
      if (submitBtn) submitBtn.disabled = false;
      if (!resp.ok || !resp.data || !resp.data.ok) {
        var msg = (resp.data && (resp.data.error || (resp.data.errors && JSON.stringify(resp.data.errors)))) || 'Could not post reply.';
        if (errBox) { errBox.textContent = msg; errBox.hidden = false; }
        if (resp.status === 429 && themeIdForm && userIdForm) {
          var secs = parseCooldownSeconds(resp.data && resp.data.error) || REPLY_COOLDOWN_SEC;
          startReplyCooldown(themeIdForm, userIdForm, secs);
        }
        return;
      }
      var html = resp.data.reply_html;
      appendReplyHtml(themeIdForm, html);
      if (resp.data.theme) applyThemeState(resp.data.theme);
      refreshSidebar();
      if (ta) {
        ta.value = '';
        autoResizeTextarea(ta);
      }
      form.hidden = true;
      if (themeIdForm && userIdForm) {
        startReplyCooldown(themeIdForm, userIdForm, REPLY_COOLDOWN_SEC);
      }
    }).catch(function () {
      if (submitBtn) submitBtn.disabled = false;
      if (errBox) { errBox.textContent = 'Network error. Try again.'; errBox.hidden = false; }
    });
  }

  // ---- polling -------------------------------------------------------------

  function pollVisibleThemes(root) {
    var url = root.getAttribute('data-mindset-themes-state-url');
    if (!url) return;
    var ids = findVisibleThemeIds();
    if (!ids.length) return;
    fetchJson(url + '?ids=' + ids.join(',')).then(function (resp) {
      if (!resp.ok || !resp.data || !resp.data.ok) return;
      (resp.data.themes || []).forEach(applyThemeState);
    }).catch(function () { /* ignore */ });

    // Also poll per-theme state for new replies (since_id).
    ids.forEach(function (id) {
      var sinceId = maxReplyIdInTheme(id);
      var perUrl = '/mindset/api/theme/' + id + '/state/?since_id=' + sinceId;
      fetchJson(perUrl).then(function (resp) {
        if (!resp.ok || !resp.data || !resp.data.ok) return;
        applyThemeState(resp.data);
        var newReplies = resp.data.new_replies_html || [];
        newReplies.forEach(function (html) {
          // Avoid double-inserting if reply already in DOM (race with author tab).
          appendReplyHtml(id, html);
        });
      }).catch(function () { /* ignore */ });
    });
  }

  function pollSidebar(root) {
    var resolved = root || document.querySelector(ROOT_SELECTOR);
    if (!resolved) return;
    var url = resolved.getAttribute('data-mindset-sidebar-url');
    if (!url) return;
    fetchJson(url).then(function (resp) {
      if (!resp.ok || !resp.data || !resp.data.ok) return;
      renderSidebarList('last', resp.data.last || []);
      renderSidebarList('top', resp.data.top || []);
    }).catch(function () { /* ignore */ });
  }

  // Public hook so any delete/create/reply path can force-refresh the sidebar.
  function refreshSidebar() {
    pollSidebar();
  }

  function renderSidebarList(kind, entries) {
    var ul = document.querySelector('[data-mindset-sidebar-list="' + kind + '"]');
    if (!ul) return;
    if (!entries.length) {
      ul.innerHTML = '<li class="text-muted small">' + (kind === 'last' ? 'No themes yet.' : 'Nothing trending yet.') + '</li>';
      return;
    }
    var html = entries.map(function (e) {
      var preview = (e.preview || '').replace(/[<>&]/g, function (c) { return ({'<':'&lt;','>':'&gt;','&':'&amp;'})[c]; }) || '(no text)';
      return ''
        + '<li class="mindset-sidebar-item">'
        +   '<span class="fw-semibold primary_">@</span> '
        +   '<a class="mindset-sidebar-link" href="' + e.url + '">' + preview + '</a>'
        + '</li>';
    }).join('');
    ul.innerHTML = html;
  }

  // ---- init ----------------------------------------------------------------

  function init() {
    var root = document.querySelector(ROOT_SELECTOR);
    if (!root) return;
    bindRoot(root);
    bindDeleteModal();
    initAllReplyCooldowns(root);

    if (!root.__mindsetTimers) {
      root.__mindsetTimers = true;
      setInterval(function () { pollVisibleThemes(root); }, THEME_POLL_MS);
      setInterval(function () { pollSidebar(root); }, SIDEBAR_POLL_MS);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  document.addEventListener('turbo:load', init);
})();
