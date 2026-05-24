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
  var THEME_CREATE_COOLDOWN_SEC = 60;
  var THEME_CREATE_COOLDOWN_KEY_PREFIX = 'mindset_theme_create_until_';
  var MINDSET_WALL_PAGE_STORAGE_PREFIX = 'mindsetWallPages:';

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
    btn.setAttribute('aria-label', liked ? 'Unlike' : 'Like');
    var heart = btn.querySelector('i.fa');
    if (heart) heart.className = 'fa ' + (liked ? 'fa-heart' : 'fa-heart-o');
    var label = btn.querySelector('span');
    if (label) label.textContent = liked ? 'Liked' : 'Like';
  }

  function paintRepostButton(btn, reposted) {
    if (!btn) return;
    btn.classList.toggle('is-active', !!reposted);
    btn.setAttribute('aria-pressed', reposted ? 'true' : 'false');
    btn.setAttribute('aria-label', reposted ? 'Undo repost' : 'Repost');
    var label = btn.querySelector('span');
    if (label) label.textContent = reposted ? 'Reposted' : 'Repost';
  }

  /**
   * Update Follow/Followed links on every theme card by the same author so
   * clicking once on any card flips them all in lockstep.
   */
  function paintFollowLinksByUsername(username, following) {
    if (!username) return;
    var safe = String(username).replace(/(["\\])/g, '\\$1');
    var sel = '[data-action="follow-user"][data-username="' + safe + '"]';
    document.querySelectorAll(sel).forEach(function (link) {
      link.classList.toggle('is-following', !!following);
      link.setAttribute('aria-pressed', following ? 'true' : 'false');
      var label = link.querySelector('.mindset-follow-link__label') ||
                  link.querySelector('span');
      if (label) label.textContent = following ? 'Followed' : 'Follow';
      var check = link.querySelector('.mindset-follow-link__check');
      if (check) {
        if (following) {
          check.removeAttribute('hidden');
        } else {
          check.setAttribute('hidden', '');
        }
      }
    });
  }

  function ensureFollowingWallEmptyState(feedList) {
    var root = document.querySelector(ROOT_SELECTOR);
    if (!root || root.getAttribute('data-mindset-wall') !== 'following') return;
    if (!feedList) feedList = root.querySelector('[data-mindset-feed-list]');
    if (!feedList) return;
    if (feedList.querySelector('article.mindset-theme')) return;
    if (feedList.querySelector('.mindset-following-wall-empty')) return;
    var pag = feedList.querySelector('#mindsetListPagination');
    if (pag) pag.remove();
    var empty = document.createElement('div');
    empty.className = 'mindset-empty text-muted text-center py-5 mindset-following-wall-empty';
    empty.innerHTML =
      '<p class="m-0">No themes from people you follow yet.</p>' +
      '<p class="small m-0 mt-2">Follow authors from the <b class="primary_">Main wall</b> to see their themes here.</p>';
    feedList.appendChild(empty);
  }

  /**
   * On Following wall, unfollowing an author removes their theme cards with the
   * same collapse animation as profile un-repost.
   */
  function removeFollowingWallCardsOnUnfollow(authorUsername) {
    if (!authorUsername) return;
    var root = document.querySelector(ROOT_SELECTOR);
    if (!root || root.getAttribute('data-mindset-wall') !== 'following') return;
    var list = root.querySelector('[data-mindset-feed-list]');
    if (!list) return;
    list.querySelectorAll('article.mindset-theme[data-mindset-author]').forEach(function (card) {
      if (card.getAttribute('data-mindset-author') === authorUsername) {
        animatedRemove(card);
      }
    });
  }

  /**
   * Animated collapse + removal of any feed entry block. Used for:
   *   - un-repost on the /profile/<u>/themes/?tab=reposts page
   *     (target = .profile-mindset-repost-block);
   *   - the user deleting their own theme / reply / repost via the confirm
   *     modal on /profile/<u>/themes/ (target = the appropriate wrapper).
   *
   * Height + margin animate to 0, then the element is removed from the DOM
   * and the empty-state placeholder is re-rendered if the tab is now empty.
   * Falls back to an instant remove if `prefers-reduced-motion` is set.
   */
  function animatedRemove(block) {
    if (!block || block.dataset.mindsetRemoving === '1') return;
    block.dataset.mindsetRemoving = '1';

    var prefersReduced = false;
    try {
      prefersReduced =
        window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (_) { /* ignore */ }

    function finalize() {
      var feedRoot = block.closest('[data-mindset-feed]');
      if (block.parentNode) {
        block.parentNode.removeChild(block);
      }
      maybeShowProfileEmpty(feedRoot);
      if (feedRoot && feedRoot.getAttribute('data-mindset-wall') === 'following') {
        var list = feedRoot.querySelector('[data-mindset-feed-list]');
        window.setTimeout(function () {
          ensureFollowingWallEmptyState(list);
        }, 0);
      }
    }

    if (prefersReduced) {
      finalize();
      return;
    }

    var rect = block.getBoundingClientRect();
    var cs = window.getComputedStyle(block);
    var mt = parseFloat(cs.marginTop) || 0;
    var mb = parseFloat(cs.marginBottom) || 0;

    block.style.height = rect.height + 'px';
    block.style.marginTop = mt + 'px';
    block.style.marginBottom = mb + 'px';
    block.style.overflow = 'hidden';
    block.classList.add('mindset-collapsing');
    if (block.classList.contains('profile-mindset-repost-block')) {
      block.classList.add('profile-mindset-repost-block--removing');
    }

    void block.offsetHeight;

    block.style.height = '0px';
    block.style.marginTop = '0px';
    block.style.marginBottom = '0px';
    block.style.opacity = '0';
    block.style.transform = 'translateY(-4px)';

    var done = false;
    function onEnd(e) {
      if (e && e.target !== block) return;
      if (e && e.propertyName && e.propertyName !== 'height' && e.propertyName !== 'opacity') return;
      if (done) return;
      done = true;
      block.removeEventListener('transitionend', onEnd);
      finalize();
    }
    block.addEventListener('transitionend', onEnd);
    setTimeout(function () { onEnd(); }, 520);
  }

  /**
   * For an arbitrary element inside the profile mindset feed, return the
   * outer entry wrapper that should be collapsed/removed (so the surrounding
   * "Reposted: ..." header or the wrapping div disappear together with the
   * theme/reply). On non-profile pages we just collapse the element itself.
   */
  function findProfileEntryWrapper(el) {
    if (!el) return null;
    return (
      el.closest('.profile-mindset-repost-block') ||
      el.closest('.profile-reposts-reply-wrap') ||
      el
    );
  }

  function getActiveProfileTab() {
    try {
      var t = (new URL(window.location.href)).searchParams.get('tab') || 'themes';
      t = String(t).toLowerCase();
      if (t === 'root') t = 'themes';
      return (t === 'replies' || t === 'reposts') ? t : 'themes';
    } catch (_) {
      return 'themes';
    }
  }

  function maybeShowProfileEmpty(feedRoot) {
    if (!feedRoot) return;
    if (!feedRoot.classList.contains('profile-reposts-page')) return;
    var list = feedRoot.querySelector('[data-mindset-feed-list]');
    if (!list) return;
    var entrySel =
      ':scope > .mindset-theme, ' +
      ':scope > .profile-reposts-reply-wrap, ' +
      ':scope > .profile-mindset-repost-block';
    if (list.querySelector(entrySel)) return;
    if (list.querySelector('.mindset-empty')) return;

    var tab = getActiveProfileTab();
    var msg = tab === 'replies'
      ? 'No replies yet.'
      : tab === 'reposts'
        ? 'No reposts yet.'
        : 'No themes yet.';

    var empty = document.createElement('div');
    empty.className = 'mindset-empty text-muted py-5';
    var p = document.createElement('p');
    p.className = 'm-0 text-center';
    p.textContent = msg;
    empty.appendChild(p);
    var pagination = list.querySelector(':scope > .w-100');
    if (pagination) {
      list.insertBefore(empty, pagination);
    } else {
      list.appendChild(empty);
    }
  }

  function themeCounterValue(state, kind) {
    if (!state) return null;
    if (kind === 'replies') {
      return state.replies_count_human != null ? state.replies_count_human : state.replies_count;
    }
    if (kind === 'likes') {
      return state.likes_count_human != null ? state.likes_count_human : state.likes_count;
    }
    if (kind === 'reposts') {
      return state.reposts_count_human != null ? state.reposts_count_human : state.reposts_count;
    }
    return null;
  }

  /** Instant counter sync for sidebar rows (same theme id as feed cards). */
  function applySidebarThemeCounters(state) {
    if (!state || state.id == null) return;
    var item = document.querySelector('[data-mindset-sidebar-theme="' + state.id + '"]');
    if (!item) return;
    setCounter(item, 'replies', themeCounterValue(state, 'replies'));
    setCounter(item, 'likes', themeCounterValue(state, 'likes'));
    setCounter(item, 'reposts', themeCounterValue(state, 'reposts'));
  }

  /**
   * Apply state to a theme card. ``opts.skip`` is a Set of buttons to skip
   * ("like" or "repost") — used to keep the button the user just clicked
   * authoritative when the OTHER button's response arrives.
   */
  function applyThemeState(state, opts) {
    if (!state || !state.id) return;
    opts = opts || {};
    applySidebarThemeCounters(state);

    var card = document.querySelector('[data-mindset-theme="' + state.id + '"]');
    if (!card) return;
    setCounter(card, 'replies', themeCounterValue(state, 'replies'));
    setCounter(card, 'likes', themeCounterValue(state, 'likes'));
    setCounter(card, 'reposts', themeCounterValue(state, 'reposts'));

    if (!opts.skipLike && state.user_liked !== undefined) {
      paintLikeButton(card.querySelector('[data-action="like"]'), state.user_liked);
    }
    if (!opts.skipRepost && state.user_reposted !== undefined) {
      paintRepostButton(card.querySelector('[data-action="repost"]'), state.user_reposted);
    }
    if (state.user_following_author !== undefined) {
      var followAuthor = state.author_username ||
        (card.getAttribute('data-mindset-author') || '');
      if (followAuthor) {
        paintFollowLinksByUsername(followAuthor, !!state.user_following_author);
      }
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
    var raw = r ? (r.getAttribute('data-user-id') || '').trim() : '';
    return raw;
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

  // ---- "Add theme" cooldown (60s after publish, per user; like comment_form) -

  function themeCreateCooldownStorageKey(userId) {
    if (!userId) return null;
    return THEME_CREATE_COOLDOWN_KEY_PREFIX + userId;
  }

  function getThemeCreateCooldownRemaining(userId) {
    var key = themeCreateCooldownStorageKey(userId);
    if (!key) return 0;
    var until = Number(localStorage.getItem(key) || 0);
    var diff = Math.ceil((until - Date.now()) / 1000);
    return diff > 0 ? diff : 0;
  }

  function syncOneMindsetNewThemeBtn(el, userId) {
    if (!el || !userId) return;
    if (!el.dataset.mindsetNewLabel) {
      el.dataset.mindsetNewLabel = el.textContent.trim();
    }
    if (!el.dataset.mindsetNewHref) {
      el.dataset.mindsetNewHref = el.getAttribute('href') || '';
    }
    var left = getThemeCreateCooldownRemaining(userId);
    if (left > 0) {
      el.classList.add('is-blocked');
      el.setAttribute('aria-disabled', 'true');
      el.setAttribute('href', '#');
      el.textContent = 'Wait ' + left + 's';

      if (el.__themeCreateCooldownTimer) {
        clearInterval(el.__themeCreateCooldownTimer);
        el.__themeCreateCooldownTimer = null;
      }
      el.__themeCreateCooldownTimer = setInterval(function () {
        var rem = getThemeCreateCooldownRemaining(userId);
        if (rem <= 0) {
          clearInterval(el.__themeCreateCooldownTimer);
          el.__themeCreateCooldownTimer = null;
          var k = themeCreateCooldownStorageKey(userId);
          if (k) localStorage.removeItem(k);
          el.classList.remove('is-blocked');
          el.removeAttribute('aria-disabled');
          el.textContent = el.dataset.mindsetNewLabel || 'Add theme';
          var h = el.dataset.mindsetNewHref;
          if (h) el.setAttribute('href', h);
          return;
        }
        el.textContent = 'Wait ' + rem + 's';
      }, 1000);
      return;
    }

    if (el.__themeCreateCooldownTimer) {
      clearInterval(el.__themeCreateCooldownTimer);
      el.__themeCreateCooldownTimer = null;
    }
    el.classList.remove('is-blocked');
    el.removeAttribute('aria-disabled');
    el.textContent = el.dataset.mindsetNewLabel || 'Add theme';
    var hrefBack = el.dataset.mindsetNewHref;
    if (hrefBack) el.setAttribute('href', hrefBack);
  }

  function consumeThemePostedQuery(userId) {
    try {
      var u = new URL(window.location.href);
      if (u.searchParams.get('theme_posted') !== '1') return;
      if (!userId) return;
      u.searchParams.delete('theme_posted');
      var qs = u.searchParams.toString();
      var clean = u.pathname + (qs ? '?' + qs : '') + u.hash;
      window.history.replaceState({}, '', clean);
      var key = themeCreateCooldownStorageKey(userId);
      if (key) {
        localStorage.setItem(key, String(Date.now() + THEME_CREATE_COOLDOWN_SEC * 1000));
      }
    } catch (_) { /* ignore */ }
  }

  function initMindsetNewThemeCooldown(root) {
    var userId = getUserId(root);
    if (!userId) return;
    consumeThemePostedQuery(userId);
    document.querySelectorAll('a.mindset-new-btn').forEach(function (el) {
      syncOneMindsetNewThemeBtn(el, userId);
    });
  }

  // ---- action handlers (instant for the actor) -----------------------------

  function bindRoot(root) {
    if (root.__mindsetBound) return;
    root.__mindsetBound = true;
    var auth = String(root.getAttribute('data-user-authenticated') || '').trim() === '1';

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

      if (action === 'follow-user') {
        if (!auth) return;
        var fUrl = btn.getAttribute('data-url');
        var fUser = btn.getAttribute('data-username');
        if (!fUrl || !fUser || btn.getAttribute('aria-busy') === 'true') return;
        btn.setAttribute('aria-busy', 'true');
        postForm(fUrl).then(function (resp) {
          btn.removeAttribute('aria-busy');
          if (resp.ok && resp.data && resp.data.ok) {
            var uname = resp.data.username || fUser;
            var nowFollowing = !!resp.data.following;
            paintFollowLinksByUsername(uname, nowFollowing);
            if (!nowFollowing) {
              removeFollowingWallCardsOnUnfollow(uname);
            }
          } else if (resp.data && resp.data.error) {
            console.warn('Mindset:', resp.data.error);
          }
        }).catch(function () { btn.removeAttribute('aria-busy'); });
        return;
      }

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
        var themeRepostBlock =
          action === 'repost' ? btn.closest('.profile-mindset-repost-block') : null;
        btn.disabled = true;
        postForm(url).then(function (resp) {
          btn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok && resp.data.theme) {
            applyThemeState(resp.data.theme);
            if (
              themeRepostBlock &&
              resp.data.theme.user_reposted === false
            ) {
              animatedRemove(themeRepostBlock);
            }
          } else if (resp.data && resp.data.error) {
            console.warn('Mindset:', resp.data.error);
          }
        }).catch(function () { btn.disabled = false; });
        return;
      }

      if (action === 'reply-like' || action === 'reply-repost') {
        var rurl = btn.getAttribute('data-url');
        if (!rurl || btn.disabled) return;
        var replyRepostBlock =
          action === 'reply-repost' ? btn.closest('.profile-mindset-repost-block') : null;
        btn.disabled = true;
        postForm(rurl).then(function (resp) {
          btn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok && resp.data.reply) {
            applyReplyState(resp.data.reply);
            if (
              replyRepostBlock &&
              resp.data.reply.user_reposted === false
            ) {
              animatedRemove(replyRepostBlock);
            }
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

    root.addEventListener('input', function (ev) {
      var ta = ev.target;
      if (!ta || !ta.matches('form[data-mindset-reply-form] textarea[name="body"]')) return;
      var form = ta.closest('form');
      if (!form) return;
      var errBox = form.querySelector('[data-mindset-reply-error]');
      if (errBox && !errBox.hidden && errBox.dataset.kind !== 'image') {
        errBox.textContent = '';
        errBox.hidden = true;
      }
    });
  }

  // ---- Delete confirmation modal ------------------------------------------

  /** Bootstrap Modal always calls ScrollBarHelper.hide() (body overflow:hidden),
   *  which breaks position:sticky on the mindset sidebar and filter tabs. */
  function releaseMindsetDeleteModalScrollLock(modalEl) {
    if (!modalEl) return;
    try {
      var inst = window.bootstrap && window.bootstrap.Modal.getInstance(modalEl);
      if (inst && inst._scrollBar && typeof inst._scrollBar.reset === 'function') {
        inst._scrollBar.reset();
      }
    } catch (e) { /* ignore */ }
    document.body.style.overflow = '';
    document.body.style.removeProperty('padding-right');
    document.body.style.removeProperty('padding-left');
  }

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

      releaseMindsetDeleteModalScrollLock(modal);
    });

    modal.addEventListener('shown.bs.modal', function () {
      releaseMindsetDeleteModalScrollLock(modal);
    });

    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        if (!ctx.url) return;
        confirmBtn.disabled = true;
        postForm(ctx.url).then(function (resp) {
          confirmBtn.disabled = false;
          if (resp.ok && resp.data && resp.data.ok) {
            // Hide the confirm modal first so its closing animation can run in
            // parallel with the entry's collapse animation (better perceived
            // responsiveness, and avoids any focus-trap fights with a soon-to-
            // be-removed node).
            try {
              var inst = window.bootstrap && window.bootstrap.Modal.getInstance(modal);
              if (inst) inst.hide();
            } catch (e) { /* ignore */ }

            if (ctx.kind === 'theme') {
              document
                .querySelectorAll('[data-mindset-theme="' + ctx.id + '"]')
                .forEach(function (card) {
                  animatedRemove(findProfileEntryWrapper(card));
                });
            } else {
              document
                .querySelectorAll('[data-mindset-reply="' + ctx.id + '"]')
                .forEach(function (node) {
                  animatedRemove(findProfileEntryWrapper(node));
                });
              if (resp.data.theme) applyThemeState(resp.data.theme);
            }
            refreshSidebar();
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

  // ---- reply image attach (single optional file) ---------------------------

  var REPLY_IMAGE_MIME = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  var REPLY_IMAGE_MAX_BYTES = 8 * 1024 * 1024; // mirrors smart_blog limit

  function clearReplyImagePreview(form) {
    var input = form.querySelector('[data-mindset-reply-image-input]');
    var preview = form.querySelector('[data-mindset-reply-image-preview]');
    var errBox = form.querySelector('[data-mindset-reply-error]');
    if (input) { try { input.value = ''; } catch (_) { input.value = null; } }
    if (preview) { preview.innerHTML = ''; preview.hidden = true; }
    if (errBox) {
      errBox.textContent = '';
      errBox.hidden = true;
      delete errBox.dataset.kind;
    }
  }

  function formatReplyFormError(data) {
    if (!data) return 'Could not post reply.';
    if (data.error) return data.error;
    if (data.errors) {
      if (data.errors.body && data.errors.body.length) return data.errors.body[0];
      if (data.errors.__all__ && data.errors.__all__.length) return data.errors.__all__[0];
      var keys = Object.keys(data.errors);
      for (var i = 0; i < keys.length; i++) {
        var msgs = data.errors[keys[i]];
        if (msgs && msgs.length) return msgs[0];
      }
    }
    return 'Could not post reply.';
  }

  function renderReplyImagePreview(form, file) {
    var preview = form.querySelector('[data-mindset-reply-image-preview]');
    if (!preview) return;
    preview.innerHTML = '';
    var img = document.createElement('img');
    img.alt = '';
    img.decoding = 'async';
    var url = URL.createObjectURL(file);
    img.src = url;
    img.addEventListener('load', function () {
      try { URL.revokeObjectURL(url); } catch (_) { /* ignore */ }
    }, { once: true });
    var rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'mindset-reply-image-preview__remove';
    rm.setAttribute('aria-label', 'Remove image');
    rm.dataset.mindsetReplyImageRemove = '1';
    rm.innerHTML = '<i class="fa fa-times" aria-hidden="true"></i>';
    preview.appendChild(img);
    preview.appendChild(rm);
    preview.hidden = false;
  }

  function bindReplyImageInputs(root) {
    if (root.__mindsetReplyImageBound) return;
    root.__mindsetReplyImageBound = true;
    root.addEventListener('change', function (ev) {
      var input = ev.target;
      if (!input || !input.matches('[data-mindset-reply-image-input]')) return;
      var form = input.closest('form');
      if (!form) return;
      var file = (input.files && input.files[0]) || null;
      var errBox = form.querySelector('[data-mindset-reply-error]');
      if (!file) {
        clearReplyImagePreview(form);
        return;
      }
      var type = (file.type || '').toLowerCase();
      if (REPLY_IMAGE_MIME.indexOf(type) === -1) {
        if (errBox) {
          errBox.textContent = 'Only JPEG, PNG, or WebP images are allowed.';
          errBox.hidden = false;
          errBox.dataset.kind = 'image';
        }
        clearReplyImagePreview(form);
        return;
      }
      if (file.size > REPLY_IMAGE_MAX_BYTES) {
        if (errBox) {
          errBox.textContent = 'Image is too large (max 8 MB).';
          errBox.hidden = false;
          errBox.dataset.kind = 'image';
        }
        clearReplyImagePreview(form);
        return;
      }
      renderReplyImagePreview(form, file);
    });
    root.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-mindset-reply-image-remove]');
      if (!btn) return;
      ev.preventDefault();
      var form = btn.closest('form');
      if (form) clearReplyImagePreview(form);
    });
  }

  function submitReplyForm(form) {
    var errBox = form.querySelector('[data-mindset-reply-error]');
    if (errBox) {
      errBox.hidden = true;
      errBox.textContent = '';
      delete errBox.dataset.kind;
    }
    var submitBtn = form.querySelector('button[type="submit"]');
    var ta = form.querySelector('textarea[name="body"]');
    var imageInput = form.querySelector('[data-mindset-reply-image-input]');
    var hasImage = imageInput && imageInput.files && imageInput.files.length > 0;
    if (!ta || !ta.value.trim()) {
      if (errBox) { errBox.textContent = 'Reply cannot be empty.'; errBox.hidden = false; }
      return;
    }
    if (submitBtn) submitBtn.disabled = true;

    var fd = new FormData(form);
    // FormData includes empty file inputs as zero-byte uploads on some
    // browsers; strip them so the server doesn't see an "image" key it has
    // to validate just to discover the upload was unused.
    if (!hasImage) {
      try { fd.delete('image'); } catch (_) { /* ignore */ }
    }
    var themeIdForm = form.getAttribute('data-theme-id');
    var userIdForm = getUserId();
    postForm(form.action, fd).then(function (resp) {
      if (submitBtn) submitBtn.disabled = false;
      if (!resp.ok || !resp.data || !resp.data.ok) {
        var msg = formatReplyFormError(resp.data);
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
      if (ta) {
        ta.value = '';
        autoResizeTextarea(ta);
      }
      clearReplyImagePreview(form);
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
    var activeTag = (root.getAttribute('data-mindset-active-tag') || '').trim();
    var tagQuery = activeTag ? '&tag=' + encodeURIComponent(activeTag) : '';
    ids.forEach(function (id) {
      var sinceId = maxReplyIdInTheme(id);
      var perUrl = '/mindset/api/theme/' + id + '/state/?since_id=' + sinceId + tagQuery;
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

  function sidebarCounterVal(e, humanKey, rawKey) {
    if (e[humanKey] != null && e[humanKey] !== '') return String(e[humanKey]);
    return String(e[rawKey] != null ? e[rawKey] : 0);
  }

  function sidebarCountersHtml(e) {
    return ''
      + '<div class="mindset-sidebar-item__counters mindset-theme__counters" aria-label="Theme activity">'
      +   '<span class="mindset-counter" data-counter="replies">'
      +     '<i class="fa fa-comment-o" aria-hidden="true"></i>'
      +     '<span class="mindset-counter__val">' + sidebarCounterVal(e, 'replies_human', 'replies') + '</span>'
      +   '</span>'
      +   '<span class="mindset-counter" data-counter="likes">'
      +     '<i class="fa fa-heart-o" aria-hidden="true"></i>'
      +     '<span class="mindset-counter__val">' + sidebarCounterVal(e, 'likes_human', 'likes') + '</span>'
      +   '</span>'
      +   '<span class="mindset-counter" data-counter="reposts">'
      +     '<i class="fa fa-retweet" aria-hidden="true"></i>'
      +     '<span class="mindset-counter__val">' + sidebarCounterVal(e, 'reposts_human', 'reposts') + '</span>'
      +   '</span>'
      + '</div>';
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
        + '<li class="mindset-sidebar-item" data-mindset-sidebar-theme="' + e.id + '">'
        +   '<div class="mindset-sidebar-item__title">'
        +     '<span class="fw-semibold primary_">@</span> '
        +     '<a class="mindset-sidebar-link" href="' + e.url + '">' + preview + '</a>'
        +   '</div>'
        +   sidebarCountersHtml(e)
        + '</li>';
    }).join('');
    ul.innerHTML = html;
  }

  // ---- notification deep-link (#mindset-theme-<id>, #mindset-reply-<id>) ---

  function scrollMindsetAnchorIntoView(cardEl) {
    if (!cardEl) return false;
    var headerEl = document.querySelector('.header-wrapper');
    var headerH = headerEl ? Math.round(headerEl.getBoundingClientRect().height) : 64;
    var offset = headerH + 24;
    var rect = cardEl.getBoundingClientRect();
    var targetY = Math.max(0, Math.round(rect.top + window.pageYOffset - offset));
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    try {
      window.scrollTo({ top: targetY, behavior: reduce ? 'auto' : 'smooth' });
    } catch (e) {
      window.scrollTo(0, targetY);
    }
    return true;
  }

  function pulseMindsetHighlight(cardEl) {
    if (!cardEl) return;
    cardEl.classList.remove('back-highlight');
    setTimeout(function () {
      void cardEl.offsetWidth;
      cardEl.classList.add('back-highlight');
      setTimeout(function () {
        cardEl.classList.remove('back-highlight');
      }, 1900);
    }, 250);
  }

  function handleMindsetNotificationHash() {
    var raw = (location.hash || '').replace(/^#/, '');
    if (!raw) return;
    if (raw.indexOf('mindset-theme-') !== 0 && raw.indexOf('mindset-reply-') !== 0) return;
    var el = document.getElementById(raw);
    if (!el) return;
    requestAnimationFrame(function () {
      scrollMindsetAnchorIntoView(el);
      pulseMindsetHighlight(el);
    });
  }

  // ---- wall tabs (Main wall / Following wall) without reload --------------

  function appendPartialFlag(url) {
    var sep = url.indexOf('?') === -1 ? '?' : '&';
    return url + sep + 'partial=1';
  }

  function stripPartialFlag(url) {
    return url
      .replace(/([?&])partial=1(&|$)/, function (_m, lead, tail) {
        return tail === '&' ? lead : (lead === '?' ? '' : '');
      })
      .replace(/\?$/, '');
  }

  function mindsetWallPageStorageKey(pathname) {
    return MINDSET_WALL_PAGE_STORAGE_PREFIX + pathname;
  }

  function readMindsetWallPages(pathname) {
    try {
      return JSON.parse(sessionStorage.getItem(mindsetWallPageStorageKey(pathname)) || '{}');
    } catch (_) {
      return {};
    }
  }

  function writeMindsetWallPage(pathname, wallKey, page) {
    var map = readMindsetWallPages(pathname);
    map[wallKey] = page;
    try {
      sessionStorage.setItem(mindsetWallPageStorageKey(pathname), JSON.stringify(map));
    } catch (_) { /* ignore quota / private mode */ }
  }

  function persistCurrentMindsetWallPage(root) {
    if (!root || root.getAttribute('data-user-authenticated') !== '1') return;
    var wall = root.getAttribute('data-mindset-wall') || 'main';
    var wallKey = wall === 'following' ? 'following' : 'main';
    var pathname = window.location.pathname;
    var params = new URLSearchParams(window.location.search);
    var page = parseInt(params.get('page') || '1', 10);
    if (!isFinite(page) || page < 1) page = 1;
    writeMindsetWallPage(pathname, wallKey, page);
  }

  function urlWithRememberedWallPage(href, targetMode) {
    var u = new URL(href, window.location.origin);
    var pathname = u.pathname;
    var map = readMindsetWallPages(pathname);
    var wallKey = targetMode === 'following' ? 'following' : 'main';
    var page = map[wallKey];
    if (page && page > 1) {
      u.searchParams.set('page', String(page));
    } else {
      u.searchParams.delete('page');
    }
    return u.pathname + u.search + u.hash;
  }

  function setActiveWallTab(tabsRoot, mode) {
    if (!tabsRoot) return;
    tabsRoot.querySelectorAll('.filter-reason-btn').forEach(function (a) {
      var isFollowing = (a.getAttribute('href') || '').indexOf('wall=following') !== -1;
      var thisMode = isFollowing ? 'following' : 'main';
      var selected = thisMode === mode;
      a.classList.toggle('is-selected', selected);
      if (selected) {
        a.setAttribute('aria-current', 'page');
      } else {
        a.removeAttribute('aria-current');
      }
    });
  }

  function refreshFeedAfterPartial(root) {
    initAllReplyCooldowns(root);
  }

  var wallNavInFlight = null;

  function loadWall(root, targetUrl, mode, opts) {
    opts = opts || {};
    var feedList = root.querySelector('[data-mindset-feed-list]');
    if (!feedList) {
      window.location.href = targetUrl;
      return;
    }
    var tabs = root.querySelector('.mindset-wall-tabs');

    if (wallNavInFlight) {
      try { wallNavInFlight.abort(); } catch (_) { /* ignore */ }
    }
    var ctrl = window.AbortController ? new AbortController() : null;
    wallNavInFlight = ctrl;

    feedList.classList.add('mindset-feed--loading');

    fetch(appendPartialFlag(targetUrl), {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html' },
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function (html) {
        feedList.innerHTML = html;
        feedList.classList.remove('mindset-feed--loading');
        root.setAttribute('data-mindset-wall', mode);
        setActiveWallTab(tabs, mode);

        if (!opts.skipHistory) {
          var visibleUrl = stripPartialFlag(targetUrl);
          window.history.pushState({ mindsetWall: mode, url: visibleUrl }, '', visibleUrl);
        }

        persistCurrentMindsetWallPage(root);

        refreshFeedAfterPartial(root);

        try {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (_) {
          window.scrollTo(0, 0);
        }
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        feedList.classList.remove('mindset-feed--loading');
        window.location.href = targetUrl;
      })
      .then(function () {
        if (wallNavInFlight === ctrl) wallNavInFlight = null;
      });
  }

  function bindWallTabs(root) {
    if (root.__mindsetWallBound) return;
    root.__mindsetWallBound = true;
    var tabsRoot = root.querySelector('.mindset-wall-tabs');
    if (!tabsRoot) return;
    tabsRoot.addEventListener('click', function (ev) {
      var link = ev.target.closest('.filter-reason-btn');
      if (!link || !tabsRoot.contains(link)) return;
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button === 1) return;
      var href = link.getAttribute('href') || '';
      if (!href) return;
      ev.preventDefault();
      var mode = href.indexOf('wall=following') !== -1 ? 'following' : 'main';
      if ((root.getAttribute('data-mindset-wall') || 'main') === mode) return;
      var targetUrl = urlWithRememberedWallPage(href, mode);
      loadWall(root, targetUrl, mode);
    });

    window.addEventListener('popstate', function () {
      var url = window.location.pathname + window.location.search;
      var mode = url.indexOf('wall=following') !== -1 ? 'following' : 'main';
      var current = root.getAttribute('data-mindset-wall') || 'main';
      if (mode === current) return;
      loadWall(root, url, mode, { skipHistory: true });
    });
  }

  // ---- init ----------------------------------------------------------------

  function init() {
    var root = document.querySelector(ROOT_SELECTOR);
    if (!root) return;
    bindRoot(root);
    bindDeleteModal();
    bindWallTabs(root);
    bindReplyImageInputs(root);
    initAllReplyCooldowns(root);
    initMindsetNewThemeCooldown(root);
    handleMindsetNotificationHash();
    persistCurrentMindsetWallPage(root);

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
  window.addEventListener('hashchange', handleMindsetNotificationHash);
})();
