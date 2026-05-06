// static/js/comments.js
(function () {
  'use strict';

  /* ===============================
     CSRF
  =============================== */
  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))
      ?.split('=')[1];
  }

  async function parseJsonSafeReply(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  async function parseJsonSafe(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  async function parseJsonSafe(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  const CSRF = getCookie('csrftoken');

  async function parseJsonSafe(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  /* ===============================
     LISTING COMMENTS SYNC
  =============================== */
  function updateListingComments(itemId, count) {
    if (!itemId) return;

    let changes = {};
    try {
      changes = JSON.parse(sessionStorage.getItem('listing_changes') || '{}');
    } catch {
      changes = {};
    }

    if (!changes[itemId]) changes[itemId] = {};
    changes[itemId].comments_count = count;

    sessionStorage.setItem('listing_changes', JSON.stringify(changes));
  }

  /* ===============================
     UI HELPERS
  =============================== */
  function humanCount(n) {
    n = Number(n);
    if (n < 1000) return String(n);
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(n);
  }

  function updateDetailCounter(count) {
    const txt = humanCount(count);
    const el = document.getElementById('commentsCount');
    if (el) el.textContent = txt;
    document.querySelectorAll('.js-item-detail-comments-count').forEach(function (node) {
      node.textContent = txt;
    });
  }

  function syncItemDetailCommentsShell(rootCount) {
    const n = Number(rootCount);
    const section = document.getElementById('detailCommentsSection');
    const emptyEl = document.getElementById('detailCommentsEmpty');
    if (section) {
      if (n > 0) section.removeAttribute('hidden');
      else section.setAttribute('hidden', '');
    }
    if (emptyEl) {
      if (n > 0) emptyEl.setAttribute('hidden', '');
      else emptyEl.removeAttribute('hidden');
    }
    const readWrap = document.getElementById('detailCommentsReadMoreWrap');
    const preview = document.getElementById('commentsListPreview');
    if (readWrap && preview) {
      const th = parseInt(preview.dataset.previewLimit || '10', 10) || 10;
      if (n > th) readWrap.removeAttribute('hidden');
      else readWrap.setAttribute('hidden', '');
    }
  }

  /** Detail preview: roots are newest-first (same idea as liked-users queue). Cap at max roots; drop the oldest visible (end of list). */
  function trimDetailCommentsPreview(preview) {
    if (!preview) return;
    const max = parseInt(preview.dataset.previewLimit || '10', 10) || 10;
    const roots = preview.querySelectorAll(':scope > .comment-block');
    if (roots.length <= max) return;
    for (let i = max; i < roots.length; i++) {
      roots[i].remove();
    }
  }

  function getRootCommentsContainer() {
    return document.getElementById('commentsListPreview') || document.getElementById('commentsList');
  }

  function updateCardCounter(itemId, count) {
    const el = document.getElementById('comments-count-' + itemId);
    if (el) el.textContent = humanCount(count);
  }

  function updateCommentsHeader(count) {
    const header = document.getElementById('commentsHeader');
    if (!header) return;

    const n = Number(count);
    if (n > 0) {
      header.innerHTML = `
        <h5 class="m-0 text-muted ">Comments</h5>
        <div class="vr comments-header-divider align-self-stretch flex-shrink-0 my-1" role="presentation"></div>
        <div class="item-stats item-stats--feed item-stats--solo d-inline-flex align-items-center">
          <div class="stat stat--comments">
            <span id="commentsCount">${humanCount(n)}</span>
            <i class="fa fa-comment" aria-hidden="true"></i>
          </div>
        </div>
      `;
    } else {
      header.innerHTML = `<h5 class="m-0 text-muted">There are not comments yet</h5>`;
    }
  }

  function getThreadLinkCount(link) {
    if (!link) return 0;
    const fromData = parseInt(link.dataset.count || '0', 10);
    if (!Number.isNaN(fromData) && fromData >= 0) return fromData;
    const span = link.querySelector('.replies-count');
    if (!span) return 0;
    const txt = (span.textContent || '').replace(/[()\s]/g, '');
    const num = parseInt(txt, 10);
    return Number.isNaN(num) ? 0 : num;
  }

  function countDirectReplyBlocks(container) {
    if (!container) return 0;
    let count = 0;
    for (const child of container.children) {
      if (child.classList?.contains('comment-block')) count += 1;
    }
    return count;
  }
  window.countDirectReplyBlocks = countDirectReplyBlocks;

  function applyThreadLinkClasses(link) {
    if (!link) return;
    link.classList.remove(
      'text-decoration-none',
      'small',
      'd-flex',
      'gap-2',
      'align-items-center',
      'success_',
      'primary_',
      'mt-4',
      'ms-1'
    );
    link.classList.add('comment-replies-thread-link');
  }

  function formatRepliesCountLabel(count) {
    return count >= 10 ? '10+' : String(count);
  }

  function renderThreadLinkContents(link, count) {
    if (!link) return;
    link.replaceChildren();
    const label = document.createElement('span');
    label.className = 'comment-replies-toggle__label';
    label.textContent = 'View deep replies';
    const badge = document.createElement('span');
    badge.className = 'replies-count';
    badge.textContent = formatRepliesCountLabel(count);
    link.append(label, badge);
  }

  function buildThreadLink(parentId, threadUrl, count) {
    const link = document.createElement('a');
    link.id = `replies-thread-link-${parentId}`;
    link.href = threadUrl;
    link.dataset.count = String(count);
    applyThreadLinkClasses(link);
    renderThreadLinkContents(link, count);
    return link;
  }
  window.buildThreadLink = buildThreadLink;

  /** Match `replied_comments.html`: thread link lives inside `.comment-main`, after `#reply-form-*` (or after actions bar). */
  function insertThreadLinkIntoParentMain(parentComment, parentId, linkEl) {
    const main = parentComment?.querySelector?.('.comment-main');
    if (!main || !linkEl) return;
    const replyForm = main.querySelector(`#reply-form-${parentId}`);
    if (replyForm) {
      replyForm.after(linkEl);
    } else {
      const bar = main.querySelector('.comment-actions-bar');
      if (bar) bar.after(linkEl);
      else main.appendChild(linkEl);
    }
  }
  window.insertThreadLinkIntoParentMain = insertThreadLinkIntoParentMain;

  function getThreadContext() {
    const marker = document.getElementById('threadViewMarker');
    if (!marker) return null;
    return {
      parentId: marker.dataset.parentId,
      backUrl: marker.dataset.backUrl,
    };
  }
  window.getThreadContext = getThreadContext;

  /** Canonical thread path /post/<slug>/comment/<id>/thread/; legacy /blog/.../ if slug unknown. */
  function defaultThreadUrl(parentId) {
    const pid = parentId == null ? '' : String(parentId);
    if (!pid) return `${window.location.origin}/`;
    const ctx =
      document.getElementById('commentsContext') || document.getElementById('threadViewMarker');
    const slug = ctx?.dataset?.itemSlug;
    if (slug) {
      return `${window.location.origin}/post/${encodeURIComponent(slug)}/comment/${pid}/thread/`;
    }
    return `${window.location.origin}/blog/comment/${pid}/thread/`;
  }

  function setThreadLinkCount(parentId, count) {
    const link = document.getElementById('replies-thread-link-' + parentId);
    if (!link) return;
    const next = Math.max(0, count || 0);
    if (next <= 0) {
      const wrap = link.parentElement;
      link.remove();
      if (wrap && wrap.classList.contains('mt-3') && !wrap.children.length) {
        wrap.remove();
      }
      return;
    }
    link.dataset.count = String(next);
    applyThreadLinkClasses(link);
    const badge = link.querySelector('.replies-count');
    const label = link.querySelector('.comment-replies-toggle__label');
    if (!badge || !label) {
      renderThreadLinkContents(link, next);
      return;
    }
    badge.textContent = formatRepliesCountLabel(next);
  }

  function adjustThreadLinkCount(parentId, delta) {
    const link = document.getElementById('replies-thread-link-' + parentId);
    if (!link) return;
    const next = getThreadLinkCount(link) + (delta || 0);
    setThreadLinkCount(parentId, next);
  }
  window.setThreadLinkCount = setThreadLinkCount;
  window.adjustThreadLinkCount = adjustThreadLinkCount;

  function formatRepliesToggleLabel(n) {
    n = Number(n);
    if (n === 1) return '1 reply';
    return `${n} replies`;
  }

  function syncRepliesToggleVisual(btn, isExpanded) {
    if (!btn || !btn.classList.contains('comment-replies-toggle')) return;
    btn.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
    btn.classList.toggle('active', isExpanded);
  }

  function expandCommentThreadAncestors(commentEl) {
    if (!commentEl) return;
    let el = commentEl;
    for (let i = 0; i < 48 && el; i++) {
      const outer = el.closest?.('.comment-replies-outer');
      if (outer) {
        outer.classList.add('is-expanded');
        const panelId = outer.id;
        let toggle =
          panelId && document.querySelector(`[aria-controls="${panelId}"]`);
        if (!toggle) {
          const prev = outer.previousElementSibling;
          if (prev && prev.classList.contains('comment-replies-toggle')) toggle = prev;
        }
        if (toggle) syncRepliesToggleVisual(toggle, true);
      }
      const nextRoot = el.parentElement?.closest?.('.comment-block');
      if (!nextRoot || nextRoot === el) break;
      el = nextRoot;
    }
  }
  window.expandCommentThreadAncestors = expandCommentThreadAncestors;

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.comment-replies-toggle');
    if (!btn) return;
    e.preventDefault();
    const panelId = btn.getAttribute('aria-controls');
    let outer =
      panelId && document.getElementById(panelId) ? document.getElementById(panelId) : null;
    if (!outer) {
      outer = btn.nextElementSibling;
    }
    if (!outer || !outer.classList.contains('comment-replies-outer')) return;
    const expanded = outer.classList.toggle('is-expanded');
    syncRepliesToggleVisual(btn, expanded);
  });

  function ensureRepliesBucketForAjax(parentComment, parentId, opts) {
    const o = opts || {};
    const isThreadView = !!getThreadContext();
    const parentDepth = parseInt(parentComment?.dataset?.depth || '0', 10);
    const main = parentComment.querySelector('.comment-main');
    if (!main) return null;

    let bucket = main.querySelector(`.replies[data-parent-id="${parentId}"]`);
    if (bucket) return bucket;

    if (isThreadView || parentDepth >= 2) {
      const replies = document.createElement('div');
      replies.className = 'replies';
      replies.dataset.parentId = String(parentId);
      const replyFormEl = main.querySelector(`#reply-form-${parentId}`);
      if (replyFormEl) {
        replyFormEl.after(replies);
      } else {
        const bar = main.querySelector('.comment-actions-bar');
        if (bar) bar.after(replies);
        else main.appendChild(replies);
      }
      return replies;
    }

    const initialCount = o.initialCount != null ? o.initialCount : 1;
    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'comment-replies-toggle mt-2';
    toggleBtn.dataset.repliesCount = String(initialCount);
    toggleBtn.setAttribute('aria-expanded', 'false');
    const panelId = `comment-replies-panel-${parentId}`;
    toggleBtn.id = `comment-replies-toggle-${parentId}`;
    toggleBtn.setAttribute('aria-controls', panelId);
    const label = document.createElement('span');
    label.className = 'comment-replies-toggle__label';
    label.textContent = formatRepliesToggleLabel(initialCount);
    const chev = document.createElement('i');
    chev.className = 'fa fa-chevron-down comment-replies-toggle__chev';
    chev.setAttribute('aria-hidden', 'true');
    toggleBtn.append(label, chev);

    const outer = document.createElement('div');
    outer.className = 'comment-replies-outer';
    outer.id = panelId;
    outer.setAttribute('role', 'region');
    outer.setAttribute('aria-labelledby', `comment-replies-toggle-${parentId}`);
    const inner = document.createElement('div');
    inner.className = 'comment-replies-inner';
    const replies = document.createElement('div');
    replies.className = 'replies';
    replies.dataset.parentId = String(parentId);
    inner.appendChild(replies);
    outer.appendChild(inner);

    const replyFormEl = main.querySelector(`#reply-form-${parentId}`);
    const ref = replyFormEl || main.querySelector('.comment-actions-bar');
    ref.after(toggleBtn);
    toggleBtn.after(outer);
    return replies;
  }
  window.ensureRepliesBucketForAjax = ensureRepliesBucketForAjax;

  function getToggleForRepliesOuter(outer) {
    if (!outer) return null;
    if (outer.id) {
      const byAria = document.querySelector(`[aria-controls="${outer.id}"]`);
      if (byAria && byAria.classList.contains('comment-replies-toggle')) return byAria;
    }
    const prev = outer.previousElementSibling;
    if (prev && prev.classList.contains('comment-replies-toggle')) return prev;
    return null;
  }

  /** Keep replies panel open after posting a reply; user collapses manually via the toggle. */
  function expandRepliesBucketForParent(parentComment, parentId) {
    const main = parentComment?.querySelector('.comment-main');
    if (!main) return;
    const bucket = main.querySelector(`.replies[data-parent-id="${parentId}"]`);
    if (!bucket) return;
    const outer = bucket.closest('.comment-replies-outer');
    if (!outer) return;
    outer.classList.add('is-expanded');
    const btn = getToggleForRepliesOuter(outer);
    if (btn) syncRepliesToggleVisual(btn, true);
  }
  window.expandRepliesBucketForParent = expandRepliesBucketForParent;

  function bumpRepliesToggleCount(parentComment, parentId, delta) {
    const main = parentComment.querySelector('.comment-main');
    if (!main) return;
    const bucket = main.querySelector(`.replies[data-parent-id="${parentId}"]`);
    if (!bucket) return;
    const outer = bucket.closest('.comment-replies-outer');
    if (!outer) return;
    const btn = getToggleForRepliesOuter(outer);
    if (!btn) return;
    const prev = parseInt(btn.dataset.repliesCount || '0', 10);
    const next = Math.max(0, prev + (delta || 0));
    btn.dataset.repliesCount = String(next);
    const label = btn.querySelector('.comment-replies-toggle__label');
    if (label) label.textContent = formatRepliesToggleLabel(next);
  }
  window.bumpRepliesToggleCount = bumpRepliesToggleCount;

  function removeEmptyRepliesBucket(parentComment, parentId) {
    const main = parentComment.querySelector('.comment-main');
    const pid = String(parentId);
    const replies =
      main?.querySelector(`.replies[data-parent-id="${pid}"]`) ||
      parentComment.querySelector('.replies');
    if (!replies || countDirectReplyBlocks(replies) > 0) return;
    const outer = replies.closest('.comment-replies-outer');
    if (outer) {
      const toggle = getToggleForRepliesOuter(outer);
      toggle?.remove();
      outer.remove();
    } else {
      replies.remove();
    }
  }

  function showFieldError(textarea, message) {
    if (!textarea) return;

    const form = textarea.closest('form');
    if (!form) return;

    form.querySelector('.field-error')?.remove();

    if (!message) return;

    const err = document.createElement('div');
    err.className = 'field-error';
    err.textContent = message;

    const bucket = form.querySelector('.reply-form-errors');
    const fieldErrorsLikeMain =
      form.matches('.reply-comment-form') || form.matches('.comment-edit-form');
    if (bucket && !fieldErrorsLikeMain) {
      bucket.appendChild(err);
    } else {
      (textarea.closest('.form-floating') || textarea).after(err);
    }
    textarea.focus();
  }

  window.showCommentFieldError = showFieldError;

  function clearFieldError(textarea) {
    textarea?.closest('form')?.querySelector('.field-error')?.remove();
  }

  function replaceCommentFormWithShadowBanMessage() {
    const formBody = document.getElementById('commentFormBody');
    const pt4 = formBody?.previousElementSibling;
    if (pt4 && formBody) {
      pt4.innerHTML = '<div class="d-inline-flex align-items-center custom-alert custom-alert-danger"><span class="small danger_" title="You have been shadow banned">You have been shadow banned. Improve your trust score to restore access.</span></div>';
      formBody.style.display = 'none';
    }
    if (window.closeAllReplyForms) window.closeAllReplyForms();
  }

  const COMMENT_MAX_CHARS = 1500;

  function countCommentChars(value) {
    return String(value || '').replace(/\r?\n/g, '').length;
  }

  function enforceCommentLimit(textarea, errorContainer = null) {
    if (!textarea) return true;
    const count = countCommentChars(textarea.value);
    if (count <= COMMENT_MAX_CHARS) {
      if (errorContainer) errorContainer.textContent = '';
      else clearFieldError(textarea);
      return true;
    }
    const msg = `Maximum ${COMMENT_MAX_CHARS} characters (line breaks are not counted).`;
    if (errorContainer) {
      errorContainer.textContent = msg;
    } else {
      showFieldError(textarea, msg);
    }
    return false;
  }
  window.enforceCommentLimit = enforceCommentLimit;

  document.addEventListener('input', (e) => {
    const ta = e.target;
    if (ta.tagName !== 'TEXTAREA' || ta.name !== 'text') return;
    const replyForm = ta.closest('.reply-comment-form');
    if (!replyForm) return;
    enforceCommentLimit(ta);
  });

  /* ===============================
     ADD COMMENT
  =============================== */
  const COMMENT_COOLDOWN_SEC = 30;
  const COMMENT_COOLDOWN_KEY_PREFIX = 'comment_cooldown_until_';

  /** Per-user + per-item; otherwise another account on same browser inherits the timer. */
  function commentCooldownStorageKey(itemId, userId) {
    if (!itemId || userId === undefined || userId === null || userId === '') return null;
    return `${COMMENT_COOLDOWN_KEY_PREFIX}${userId}_${itemId}`;
  }

  function getCooldownRemaining(itemId, userId) {
    const key = commentCooldownStorageKey(itemId, userId);
    if (!key) return 0;
    const until = Number(localStorage.getItem(key) || 0);
    const diff = Math.ceil((until - Date.now()) / 1000);
    return diff > 0 ? diff : 0;
  }

  function updateCommentButtonCooldown(btn, itemId, userId) {
    if (!btn || !itemId) return;

    const remaining = getCooldownRemaining(itemId, userId);
    const originalText =
      btn.dataset.originalText || btn.textContent || 'Comment';

    if (!btn.dataset.originalText) {
      btn.dataset.originalText = originalText;
    }

    if (remaining > 0) {
      btn.disabled = true;
      btn.classList.add('is-blocked');
      btn.textContent = `Blocked ${remaining}s`;

      if (!btn.__cooldownTimer) {
        btn.__cooldownTimer = setInterval(() => {
          const left = getCooldownRemaining(itemId, userId);
          if (left <= 0) {
            clearInterval(btn.__cooldownTimer);
            btn.__cooldownTimer = null;
            const key = commentCooldownStorageKey(itemId, userId);
            if (key) localStorage.removeItem(key);
            btn.disabled = false;
            btn.classList.remove('is-blocked');
            btn.textContent = btn.dataset.originalText;
            const form = btn.closest('form');
            const textarea = form?.querySelector('textarea[name="text"]');
            clearFieldError(textarea);
            return;
          }
          btn.textContent = `Blocked ${left}s`;
        }, 1000);
      }
      return;
    }

    if (btn.__cooldownTimer) {
      clearInterval(btn.__cooldownTimer);
      btn.__cooldownTimer = null;
    }
    btn.disabled = false;
    btn.classList.remove('is-blocked');
    btn.textContent = btn.dataset.originalText || originalText;
    const form = btn.closest('form');
    const textarea = form?.querySelector('textarea[name="text"]');
    clearFieldError(textarea);
  }

  function startCommentCooldown(itemId, btn = null, seconds = COMMENT_COOLDOWN_SEC, userId = null) {
    if (!itemId) return;
    const key = commentCooldownStorageKey(itemId, userId);
    if (!key) return;
    const until = Date.now() + seconds * 1000;
    localStorage.setItem(key, String(until));
    const targetBtn = btn || document.getElementById('submitCommentBtn');
    updateCommentButtonCooldown(targetBtn, itemId, userId);
  }

  /* ===============================
     REPLY COOLDOWN (30s per comment ID)
  =============================== */
  const REPLY_COOLDOWN_SEC = 30;
  const REPLY_COOLDOWN_KEY_PREFIX = 'reply_cooldown_until_';

  function getReplyCooldownRemaining(commentId) {
    if (!commentId) return 0;
    const key = `${REPLY_COOLDOWN_KEY_PREFIX}${commentId}`;
    const until = Number(localStorage.getItem(key) || 0);
    const diff = Math.ceil((until - Date.now()) / 1000);
    return diff > 0 ? diff : 0;
  }

  function renderReplyCooldownContent(btn, remaining, labelText) {
    const label = document.createElement('span');
    label.className = 'reply-cooldown-label';
    label.textContent = labelText;
    const timer = document.createElement('span');
    timer.className = 'reply-cooldown-timer';
    timer.textContent = `${remaining}s`;
    timer.setAttribute('aria-live', 'polite');
    timer.setAttribute(
      'title',
      `${remaining} seconds until Reply is available`
    );
    btn.replaceChildren(label, timer);
  }

  function updateReplyButtonCooldown(btn, commentId) {
    if (!btn || !commentId) return;
    const remaining = getReplyCooldownRemaining(commentId);
    let originalText = btn.dataset.originalReplyText;
    if (!originalText) {
      const labelEl = btn.querySelector('.reply-cooldown-label');
      originalText =
        (labelEl?.textContent || btn.textContent || 'Reply').trim() || 'Reply';
      btn.dataset.originalReplyText = originalText;
    }

    if (remaining > 0) {
      btn.disabled = true;
      btn.classList.add('is-reply-blocked');
      renderReplyCooldownContent(btn, remaining, originalText);
      if (!btn.__replyCooldownTimer) {
        btn.__replyCooldownTimer = setInterval(() => {
          const left = getReplyCooldownRemaining(commentId);
          if (left <= 0) {
            clearInterval(btn.__replyCooldownTimer);
            btn.__replyCooldownTimer = null;
            localStorage.removeItem(`${REPLY_COOLDOWN_KEY_PREFIX}${commentId}`);
            btn.disabled = false;
            btn.classList.remove('is-reply-blocked');
            btn.textContent = originalText;
            return;
          }
          const timerEl = btn.querySelector('.reply-cooldown-timer');
          if (timerEl) {
            timerEl.textContent = `${left}s`;
            timerEl.setAttribute('title', `${left} seconds until Reply is available`);
          }
        }, 1000);
      }
      return;
    }

    if (btn.__replyCooldownTimer) {
      clearInterval(btn.__replyCooldownTimer);
      btn.__replyCooldownTimer = null;
    }
    btn.disabled = false;
    btn.classList.remove('is-reply-blocked');
    btn.textContent = originalText;
  }

  function startReplyCooldown(commentId, seconds = REPLY_COOLDOWN_SEC) {
    if (!commentId) return;
    const until = Date.now() + seconds * 1000;
    localStorage.setItem(`${REPLY_COOLDOWN_KEY_PREFIX}${commentId}`, String(until));
    const sel = `.comment-menu-action[data-action="reply"][data-comment-id="${commentId}"], .btn-reply[data-comment-id="${commentId}"]`;
    document.querySelectorAll(sel).forEach(btn => {
      updateReplyButtonCooldown(btn, commentId);
    });
  }

  function initAllReplyButtonsCooldown() {
    document
      .querySelectorAll('.comment-menu-action[data-action="reply"], .btn-reply[data-comment-id]')
      .forEach(btn => {
        const commentId = btn.dataset.commentId;
        if (commentId) updateReplyButtonCooldown(btn, commentId);
      });
  }

  function parseCooldownSeconds(message) {
    if (!message) return null;
    const match = String(message).match(/(\d+)\s*second/);
    if (!match) return null;
    const n = parseInt(match[1], 10);
    return Number.isNaN(n) ? null : n;
  }

  function initClearCommentButton(textarea, clearBtn) {
    if (!textarea || !clearBtn) return;

    const toggle = () => {
      if (textarea.value.trim().length > 0) {
        clearBtn.classList.remove('hidden');
      } else {
        clearBtn.classList.add('hidden');
      }
    };

    // показываем / скрываем при вводе
    textarea.addEventListener('input', toggle);

    // очистка по клику
    clearBtn.addEventListener('click', () => {
      textarea.value = '';
      textarea.style.removeProperty('height');
      clearFieldError(textarea);
      toggle();
      textarea.focus();
    });

    // начальное состояние
    toggle();
  }
  function initAddComment() {
    const form = document.getElementById('commentForm');
    if (!form || form.__bound) return;
    form.__bound = true;

    const formBody = document.getElementById('commentFormBody');
    const toggleBtn = document.querySelector('.comment-form-btn');
    const toggleDown = toggleBtn?.querySelector('.fa-angle-down');
    const toggleUp = toggleBtn?.querySelector('.fa-angle-up');
    const btn = document.getElementById('submitCommentBtn');
    const textarea = form.querySelector('textarea[name="text"]');
    const commentsList = getRootCommentsContainer();
    const itemId = form.dataset.itemId;
    const userId = form.dataset.userId;
    const clearBtn = document.getElementById('clearComment');

    initClearCommentButton(textarea, clearBtn);
    updateCommentButtonCooldown(btn, itemId, userId);
    textarea.addEventListener('input', () => {
      if (textarea.value.trim()) {
        clearFieldError(textarea);
      }
      enforceCommentLimit(textarea);
    });

    if (toggleBtn && formBody) {
      toggleBtn.addEventListener('click', () => {
        formBody.classList.toggle('hidden');
        const isOpen = !formBody.classList.contains('hidden');
        if (toggleDown && toggleUp) {
          toggleDown.classList.toggle('hidden', isOpen);
          toggleUp.classList.toggle('hidden', !isOpen);
        }
        if (isOpen) {
          textarea?.focus();
        }
      });
    }

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      if (btn.disabled) return;
      if (getCooldownRemaining(itemId, userId) > 0) {
        updateCommentButtonCooldown(btn, itemId, userId);
        return;
      }

      clearFieldError(textarea);
      if (!enforceCommentLimit(textarea)) return;
      const text = textarea.value.trim();
      if (!text) {
        showFieldError(textarea, 'Please write a text...');
        return;
      }

      btn.disabled = true;

      try {
        const resp = await fetch(form.action, {
          method: 'POST',
          headers: {
            'X-CSRFToken': CSRF,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          },
          body: new FormData(form)
        });

        const data = await parseJsonSafe(resp);
        if (resp.ok && data?.success) {
          const count = data.comments_count;

          commentsList?.insertAdjacentHTML('afterbegin', data.comment_html);
          const preview = document.getElementById('commentsListPreview');
          if (preview && commentsList === preview) {
            trimDetailCommentsPreview(preview);
          }
          // apply long-text toggle to the new root comment immediately
          if (commentsList?.firstElementChild) {
            window.initCommentToggles?.(commentsList.firstElementChild);
            window.initCommentLikes?.();
          }

          textarea.value = '';
          textarea.style.removeProperty('height');

          // 🔥 ВАЖНО: скрываем кнопку Clear после отправки
          clearBtn?.classList.add('hidden');

          syncItemDetailCommentsShell(count);
          updateDetailCounter(count);
          updateCardCounter(itemId, count);
          updateListingComments(itemId, count);
          updateCommentsHeader(count);
          startCommentCooldown(itemId, btn, COMMENT_COOLDOWN_SEC, userId);

          return;
        }

        if (resp.status === 429) {
          const seconds = parseCooldownSeconds(data?.error);
          if (seconds) {
            startCommentCooldown(itemId, btn, seconds, userId);
          }
        }

        const errMsg = data?.error || 'Server error';
        showFieldError(textarea, errMsg);

        if (resp.status === 403) {
          replaceCommentFormWithShadowBanMessage();
        }

      } catch (err) {
        showFieldError(textarea, 'Unable to submit. Please try again.');
      } finally {
        updateCommentButtonCooldown(btn, itemId, userId);
      }
    });

    const trustStatusUrl = form.dataset.trustStatusUrl;
    if (trustStatusUrl) {
      const trustPollInterval = setInterval(async () => {
        try {
          const resp = await fetch(trustStatusUrl, {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
          });
          if (!resp.ok) return;
          const data = await parseJsonSafe(resp);
          if (data?.shadow_banned) {
            clearInterval(trustPollInterval);
            replaceCommentFormWithShadowBanMessage();
          }
        } catch (e) { /* ignore */ }
      }, 25000);
    }

    // "Please write a text" исчезает только при вводе в поле, не при клике вне формы
  }


  /* ===============================
     DELETE COMMENT
  =============================== */
  function forceCloseBootstrapModal(modalEl) {
    if (!modalEl || typeof window.bootstrap === 'undefined' || !window.bootstrap.Modal) return;
    const inst = bootstrap.Modal.getInstance(modalEl);
    if (inst) inst.hide();
    modalEl.classList.remove('show');
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.style.display = 'none';
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
    document.body.style.removeProperty('overflow');
    document.querySelectorAll('.modal-backdrop').forEach((el) => el.remove());
  }

  function initDeleteComments() {
    const modal = document.getElementById('confirmDeleteModal');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (!modal || !confirmBtn) return;

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-delete-comment');
      if (!btn) return;

      window.closeAllCommentMenus?.();

      confirmBtn.dataset.deleteUrl = btn.dataset.deleteUrl;
      confirmBtn.dataset.itemId = modal.dataset.itemId; // КЛЮЧ
    });
    confirmBtn.addEventListener('click', async () => {
      const url = confirmBtn.dataset.deleteUrl;
      const itemId = confirmBtn.dataset.itemId;
      if (!url) return;

      confirmBtn.disabled = true;

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': CSRF,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        });

        const data = await parseJsonSafe(resp);

        if (resp.ok && data?.success) {
          const deleted = document.getElementById('comment-' + data.comment_id);
          if (!deleted) return;

          const threadContext = getThreadContext();
          const isThreadRoot = threadContext && String(data.comment_id) === String(threadContext.parentId);

          if (isThreadRoot) {
            const leaveUrl =
              (window.getCommentThreadReturnUrl && window.getCommentThreadReturnUrl()) ||
              threadContext.backUrl ||
              '/';
            try {
              sessionStorage.setItem('thread_back_anchor', 'replies-thread-link-' + threadContext.parentId);
              sessionStorage.setItem('thread_back_url', leaveUrl);
              sessionStorage.setItem('thread_remove_link_' + threadContext.parentId, '1');
              sessionStorage.setItem('thread_deleted_parent_' + threadContext.parentId, '1');
            } catch { }
            if (history.length > 1) {
              history.back();
            } else {
              window.location.href = leaveUrl;
            }
            return;
          }

          function doCleanup() {
            if (data.parent_id) {
              const parentComment = document.getElementById('comment-' + data.parent_id);
              if (parentComment) {
                const pid = data.parent_id;
                bumpRepliesToggleCount(parentComment, pid, -1);
                const repliesBefore =
                  parentComment.querySelector(`.replies[data-parent-id="${pid}"]`) ||
                  parentComment.querySelector('.replies');
                if (repliesBefore && countDirectReplyBlocks(repliesBefore) === 0) {
                  removeEmptyRepliesBucket(parentComment, pid);
                }
                const ctx = getThreadContext();
                if (!ctx) {
                  const depth = parseInt(parentComment.dataset.depth || '0', 10);
                  const link = document.getElementById('replies-thread-link-' + pid);
                  const replies = parentComment.querySelector(`.replies[data-parent-id="${pid}"]`) ||
                    parentComment.querySelector('.replies');
                  if (depth >= 2) {
                    if (!replies || countDirectReplyBlocks(replies) === 0) {
                      if (link) link.remove();
                    } else if (!link) {
                      const threadUrl =
                        parentComment?.dataset?.threadUrl || defaultThreadUrl(pid);
                      const replyCount = replies ? countDirectReplyBlocks(replies) : 1;
                      insertThreadLinkIntoParentMain(
                        parentComment,
                        pid,
                        buildThreadLink(pid, threadUrl, replyCount)
                      );
                    } else {
                      window.adjustThreadLinkCount?.(pid, -1);
                    }
                  }
                }
              }
            }
            if (threadContext) {
              const tid = threadContext.parentId;
              const threadRoot = document.getElementById('comment-' + tid);
              const threadReplies = threadRoot?.querySelector('.replies');
              const threadEmpty = document.getElementById('threadEmpty');
              const rc = countDirectReplyBlocks(threadReplies);
              try { sessionStorage.setItem('thread_replies_count_' + tid, String(rc)); } catch { }
              if (!threadReplies || countDirectReplyBlocks(threadReplies) === 0) {
                try { sessionStorage.setItem('thread_remove_link_' + tid, '1'); } catch { }
                if (threadEmpty) threadEmpty.classList.remove('d-none');
              } else if (threadEmpty) threadEmpty.classList.add('d-none');
            }
            const count = data.comments_count;
            syncItemDetailCommentsShell(count);
            updateDetailCounter(count);
            updateCardCounter(itemId, count);
            updateListingComments(itemId, count);
            updateCommentsHeader(count);
          }

          forceCloseBootstrapModal(modal);
          deleted.remove();
          doCleanup();
        }
        // closeAllReplyForms();


      } catch (err) {
        console.error('Delete comment failed:', err);
      } finally {
        confirmBtn.disabled = false;
      }
    });

  }

  /* ===============================
     INIT
  =============================== */
  function handleThreadBackScroll() {
    try {
      // always remove thread links marked for deletion
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (!key || !key.startsWith('thread_remove_link_')) continue;
        const parentId = key.replace('thread_remove_link_', '');
        const link = document.getElementById('replies-thread-link-' + parentId);
        if (link) link.remove();
        sessionStorage.removeItem(key);
      }

      // remove parent comments deleted in thread view
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (!key || !key.startsWith('thread_deleted_parent_')) continue;
        const parentId = key.replace('thread_deleted_parent_', '');
        const parentNode = document.getElementById('comment-' + parentId);
        if (parentNode) parentNode.remove();
        sessionStorage.removeItem(key);
      }

      // sync replies count for thread links after returning from thread view
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (!key || !key.startsWith('thread_replies_count_')) continue;
        const parentId = key.replace('thread_replies_count_', '');
        const count = parseInt(sessionStorage.getItem(key) || '0', 10);
        const parentComment = document.getElementById('comment-' + parentId);
        if (parentComment) {
          const depth = parseInt(parentComment.dataset.depth || '0', 10);
          if (depth >= 2) {
            if (count <= 0) {
              const link = document.getElementById('replies-thread-link-' + parentId);
              if (link) link.remove();
            } else {
              let link = document.getElementById('replies-thread-link-' + parentId);
              if (!link) {
                const threadUrl =
                  parentComment?.dataset?.threadUrl || defaultThreadUrl(parentId);
                insertThreadLinkIntoParentMain(
                  parentComment,
                  parentId,
                  buildThreadLink(parentId, threadUrl, count)
                );
              } else {
                setThreadLinkCount(parentId, count);
              }
            }
          }
        }
        sessionStorage.removeItem(key);
      }

      sessionStorage.removeItem('thread_back_anchor');
      sessionStorage.removeItem('thread_back_url');
    } catch (e) { /* ignore */ }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initAddComment();
    initDeleteComments();
    handleThreadBackScroll();
  });

  window.addEventListener('pageshow', () => {
    handleThreadBackScroll();
  });

  window.getReplyCooldownRemaining = getReplyCooldownRemaining;
  window.startReplyCooldown = startReplyCooldown;
  window.initAllReplyButtonsCooldown = initAllReplyButtonsCooldown;

})();




// static/js/comment_edit.js
(function () {
  'use strict';

  /* ===============================
     Helpers
  =============================== */

  function autoResizeTextarea(textarea) {
    if (!textarea) return;
    const cs = getComputedStyle(textarea);
    const minH = parseFloat(cs.minHeight) || 0;
    const noChars = !textarea.value || textarea.value.length === 0;
    textarea.style.height = 'auto';
    const sh = textarea.scrollHeight;
    let target = Math.max(minH, sh);
    if (noChars && minH > 0 && sh > minH * 1.5) {
      target = minH;
    }
    textarea.style.height = target + 'px';
  }

  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))
      ?.split('=')[1];
  }

  const CSRF = getCookie('csrftoken');

  /* ===============================
     FIELD ERROR (как add / reply)
  =============================== */

  function showFieldError(textarea, message) {
    if (!textarea) return;

    const form = textarea.closest('form');
    if (!form) return;

    // удалить старую ошибку
    const old = form.querySelector('.field-error');
    if (old) old.remove();

    if (!message) return;

    const err = document.createElement('div');
    err.className = 'field-error';
    err.textContent = message;

    const bucket = form.querySelector('.reply-form-errors');
    const fieldErrorsLikeMain =
      form.matches('.reply-comment-form') || form.matches('.comment-edit-form');
    if (bucket && !fieldErrorsLikeMain) {
      bucket.appendChild(err);
    } else {
      (textarea.closest('.form-floating') || textarea).after(err);
    }

    textarea.focus();
  }

  function clearFieldError(textarea) {
    const form = textarea?.closest('form');
    const err = form?.querySelector('.field-error');
    if (err) err.remove();
  }

  /* ===============================
     OPEN EDITOR
  =============================== */

  function closeAllCommentEditForms() {
    document.querySelectorAll('.comment-edit-form .cancel-edit')
      .forEach(btn => btn.click());
  }

  window.closeAllCommentEditForms = closeAllCommentEditForms;

  function extractMentionUserIdFromRaw(rawDecoded) {
    if (!rawDecoded) return '';
    const m = String(rawDecoded).match(/@\[\s*user\s*:\s*(\d+)\s*\]/i);
    return m ? m[1] : '';
  }

  /** Текст для textarea: из HTML всегда через DOM textContent (никогда сырой <a>…). */
  function htmlToPlainText(html) {
    if (!html || typeof html !== 'string') return '';
    const s = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    if (!s.includes('<')) {
      return s.trim();
    }
    const d = document.createElement('div');
    d.innerHTML = s;
    return (d.textContent || d.innerText || '').replace(/\r\n/g, '\n').trim();
  }

  function openEditor(commentNode, commentId, editUrl) {
    if (window.closeAllReplyForms) {
      window.closeAllReplyForms();
    }

    const body = commentNode.querySelector('.comment-body');
    if (!body) return;

    // не открывать второй раз
    if (commentNode.querySelector('.comment-edit-form')) return;

    const originalHtml = body.innerHTML;
    const textDiv = body.querySelector('.comment-text');
    const rawHtml = commentNode.getAttribute('data-raw-html') || '';
    const editAttr = commentNode.getAttribute('data-edit-text');

    const decodeHtml = (value) => {
      if (!value) return '';
      const temp = document.createElement('textarea');
      temp.innerHTML = value;
      return temp.value;
    };

    const displayHtml =
      textDiv?.dataset.fullHtml || textDiv?.innerHTML || '';
    const rawDecoded = decodeHtml(rawHtml);

    if (displayHtml) {
      commentNode.dataset.fullHtmlCache = displayHtml;
    }

    let mentionId = (commentNode.dataset.mentionId || '').trim();
    if (!mentionId) {
      mentionId = extractMentionUserIdFromRaw(rawDecoded);
    }

    let primaryPlain = '';
    if (editAttr != null && String(editAttr).trim() !== '') {
      primaryPlain = decodeHtml(editAttr).replace(/\r\n/g, '\n').trim();
    }
    if (!primaryPlain) {
      primaryPlain =
        htmlToPlainText(rawDecoded) ||
        htmlToPlainText(displayHtml) ||
        '';
    }

    let originalText = '';
    let mention = '';
    const bodyPlain = primaryPlain;

    if (bodyPlain.startsWith('@')) {
      const comma = bodyPlain.indexOf(', ');
      if (comma === -1) {
        mention = bodyPlain.slice(1).trim();
        originalText = '';
      } else {
        mention = bodyPlain.slice(1, comma).trim();
        originalText = bodyPlain.slice(comma + 2).trim();
      }
    } else {
      originalText = bodyPlain
        .replace(/^\s*@\[user:\d+\]\s*,?\s*/i, '')
        .trim();
      const legacy = originalText.match(/^@([\w.-]+)\s*,?\s*/);
      if (legacy) {
        mention = legacy[1];
        originalText = originalText.replace(/^@[\w.-]+\s*,?\s*/, '');
      }
    }

    if (!originalText && rawDecoded) {
      const fallback = htmlToPlainText(rawDecoded)
        .replace(/^\s*@\[user:\d+\]\s*,?\s*/i, '')
        .trim();
      if (fallback) {
        originalText = fallback;
      }
    }

    /* ===============================
       FORM
    =============================== */

    const form = document.createElement('form');
    form.className = 'comment-edit-form pb-4';
    form.noValidate = true;

    const errSlot = document.createElement('div');
    errSlot.className = 'reply-form-errors mb-2';
    form.appendChild(errSlot);

    const wrap = document.createElement('div');
    wrap.className = 'mb-2';

    const textarea = document.createElement('textarea');
    textarea.name = 'text';
    textarea.className = 'form-control auto-grow';
    textarea.id = `comment-edit-text-${commentId}`;
    textarea.rows = 1;
    textarea.required = true;
    textarea.placeholder = 'Edit your comment…';
    textarea.value = originalText;

    if (mention) {
      textarea.dataset.mention = mention;
    }
    if (mentionId) {
      textarea.dataset.mentionId = mentionId;
    }

    wrap.appendChild(textarea);
    form.appendChild(wrap);

    const btnRow = document.createElement('div');
    btnRow.className = 'comment-form-actions';

    const btnSave = document.createElement('button');
    btnSave.type = 'submit';
    btnSave.className = 'cstm-btn cstm-btn-sm custom-primary-btn comment-btn';
    btnSave.textContent = 'Edit';

    const btnCancel = document.createElement('button');
    btnCancel.type = 'button';
    btnCancel.className = 'cstm-btn cstm-btn-sm custom-secondary-btn';
    btnCancel.textContent = 'Cancel';
    btnCancel.classList.add('cancel-edit');

    btnRow.appendChild(btnSave);
    btnRow.appendChild(btnCancel);
    form.appendChild(btnRow);

    body.innerHTML = '';
    body.appendChild(form);

    textarea.focus();
    if (typeof window.bindAutoGrowTextarea === 'function') {
      window.bindAutoGrowTextarea(textarea);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.syncAutoGrowTextarea?.(textarea);
        });
      });
    } else {
      autoResizeTextarea(textarea);
      textarea.addEventListener('input', () => autoResizeTextarea(textarea));
      textarea.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        requestAnimationFrame(() => autoResizeTextarea(textarea));
      });
    }
    textarea.addEventListener('input', () => {
      clearFieldError(textarea);
      if (window.enforceCommentLimit) window.enforceCommentLimit(textarea);
    });

    btnCancel.addEventListener('click', () => {
      body.innerHTML = originalHtml;

      // сбросить toggle, чтобы Show more/less снова работал
      const textEl = commentNode.querySelector('.comment-text');
      if (textEl) {
        const cached = commentNode.dataset.fullHtmlCache || textEl.innerHTML;
        textEl.innerHTML = cached;
        textEl.dataset.fullHtml = cached;
        delete textEl.dataset.toggleInit;
      }
      commentNode.querySelectorAll('.comment-toggle-btn').forEach(btn => btn.remove());

      restoreCommentUI(commentNode);
    });

    /* ===============================
       SUBMIT
    =============================== */

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      clearFieldError(textarea);

      if (window.enforceCommentLimit && !window.enforceCommentLimit(textarea)) {
        return;
      }

      let text = textarea.value.trim();
      if (!text) {
        showFieldError(textarea, 'Please write a text...');
        return;
      }

      const mentionId = (textarea.dataset.mentionId || '').trim();
      const mention = textarea.dataset.mention || '';
      if (mentionId) {
        text = text.replace(/^\s*@\[user:\d+\]\s*,?\s*/i, '').trim();
        if (mention) {
          const esc = mention.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          text = text.replace(new RegExp('^\\s*@' + esc + '\\s*,?\\s*'), '').trim();
        }
        text = `@[user:${mentionId}], ${text}`;
      } else if (mention) {
        text = `@${mention}, ${text}`;
      }

      btnSave.disabled = true;
      btnCancel.disabled = true;

      try {
        const trustStatusUrl = document.body.dataset.trustStatusUrl;
        if (trustStatusUrl) {
          try {
            const statusResp = await fetch(trustStatusUrl, {
              headers: { 'Accept': 'application/json' },
              credentials: 'same-origin'
            });
            if (statusResp.ok) {
              const statusData = await statusResp.json();
              if (statusData && statusData.shadow_banned) {
                showFieldError(textarea, 'You have been shadow banned. Improve your trust score to restore access.');
                return;
              }
            }
          } catch (e) { /* ignore */ }
        }

        const fd = new FormData();
        fd.append('text', text);

        const resp = await fetch(editUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': CSRF,
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json'
          },
          body: fd,
          credentials: 'same-origin'
        });

        const data = await resp.json().catch(() => null);
        if (resp.ok && data?.success) {
          const wrapper = document.createElement('div');
          wrapper.innerHTML = data.comment_html;

          const newNode = wrapper.firstElementChild;
          commentNode.replaceWith(newNode);
          if (window.initCommentToggles) {
            restoreCommentUI(newNode);
          }
          window.initCommentLikes?.();
          if (window.initAutoDismiss) window.initAutoDismiss(newNode);
          initEditButtons();
          return;
        }

        showFieldError(
          textarea,
          data?.errors?.text?.[0] || data?.error || 'Server error'
        );

      } catch (err) {
        showFieldError(textarea, 'Unable to save. Please try again.');
      } finally {
        btnSave.disabled = false;
        btnCancel.disabled = false;
      }

    });
  }

  /* ===============================
     INIT
  =============================== */

  function delegatedClick(e) {
    const btn = e.target.closest('.btn-edit-comment');
    if (!btn) return;

    e.preventDefault();

    const commentId = btn.dataset.commentId;
    const editUrl = btn.dataset.editUrl;

    if (!commentId || !editUrl) return;

    const commentNode = document.getElementById('comment-' + commentId);
    if (!commentNode) return;

    window.closeAllCommentMenus?.();
    openEditor(commentNode, commentId, editUrl);
  }

  function initEditButtons() {
    document.removeEventListener('click', delegatedClick);
    document.addEventListener('click', delegatedClick);
  }

  document.addEventListener('DOMContentLoaded', initEditButtons);
})();



// static/js/comment_like.js
(function () {
  'use strict';

  // get CSRF token — использую meta tag в base.html: <meta name="csrf-token" content="{{ csrf_token }}">
  function getCsrfToken() {
    // try meta tag first
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    // fallback to cookie (Django default name)
    const match = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
    return match ? match[2] : null;
  }

  function syncButtonState(btn) {
    const pressed = btn.getAttribute('aria-pressed') === 'true';
    const icon = btn.querySelector('i');
    setIconState(icon, pressed);
  }

  // helper to toggle icon classes
  function setIconState(iconEl, liked) {
    if (!iconEl) return;

    iconEl.classList.toggle('fa-thumbs-up', liked);
    iconEl.classList.toggle('fa-thumbs-o-up', !liked);
  }

  function handleClick(ev) {
    const btn = ev.currentTarget;
    if (!btn) return;
    ev.preventDefault();

    // prevent double actions
    if (btn.dataset.processing === '1') return;
    btn.dataset.processing = '1';

    const url = btn.getAttribute('data-url');
    const commentId = btn.getAttribute('data-comment-id');

    if (!url || !commentId) {
      btn.dataset.processing = '0';
      return;
    }

    const csrf = getCsrfToken();

    // send POST
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf || '',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({}) // body not needed but keep JSON in case you expand
    }).then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    }).then(data => {
      if (!data || !data.success) throw new Error('Invalid response');

      const liked = !!data.liked;
      const likesCount = data.likes_count;

      // 🔥 обновляем aria-pressed
      btn.setAttribute('aria-pressed', liked ? 'true' : 'false');

      const icon = document.getElementById('comment-like-icon-' + data.comment_id);
      const countNode = document.getElementById('comment-likes-count-' + data.comment_id);

      if (icon) {
        icon.classList.add('btn-bounce');
        setIconState(icon, liked);
        icon.addEventListener('animationend', function _onEnd() {
          icon.classList.remove('btn-bounce');
          icon.removeEventListener('animationend', _onEnd);
        });
      }

      if (countNode && typeof likesCount !== 'undefined') {
        countNode.textContent = likesCount;
      }
    }).catch(err => {
      console.error('Comment like error:', err);
      // optionally show a UI message
    }).finally(() => {
      // small delay to avoid extremely rapid re-clicks
      setTimeout(function () { btn.dataset.processing = '0'; }, 250);
    });

  }

  function init() {
    const buttons = Array.from(
      document.querySelectorAll('.btn-comment-like')
    );

    buttons.forEach(btn => {
      syncButtonState(btn);
      btn.removeEventListener('click', handleClick);
      btn.addEventListener('click', handleClick, { passive: false });
    });
  }

  window.initCommentLikes = init;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();



// ---------- Bootstrap tooltips re-init helper (FIXED) ----------
(function () {
  function initTooltips(root = document) {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;

    const elements = root.querySelectorAll('[data-bs-toggle="tooltip"]');

    elements.forEach(el => {
      // 💥 ВАЖНО: если tooltip уже был — уничтожаем
      const instance = bootstrap.Tooltip.getInstance(el);
      if (instance) {
        instance.dispose();
      }

      // создаём заново
      new bootstrap.Tooltip(el);
    });
  }

  window.initTooltips = initTooltips;

  document.addEventListener('DOMContentLoaded', () => {
    initTooltips();
  });
})();




// to top comments list
(function () {
  const btn = document.getElementById('commentsBackToTop');
  const commentsList = document.getElementById('commentsList');

  if (!btn || !commentsList) return;

  // сколько пикселей = 1–2 комментария
  const SHOW_AFTER_PX = 200;

  function checkVisibility() {
    const rect = commentsList.getBoundingClientRect();

    // если список ушёл вверх экрана
    if (rect.top < -SHOW_AFTER_PX) {
      btn.classList.add('is-visible');
    } else {
      btn.classList.remove('is-visible');
    }
  }

  window.addEventListener('scroll', checkVisibility, { passive: true });

  btn.addEventListener('click', () => {
    commentsList.scrollIntoView({
      behavior: 'auto',
      block: 'start'
    });
  });
})();



// autosize_textarea.js
(function () {
  /**
   * Высота = max(min-height, scrollHeight), чтобы одна строка текста не «подпрыгивала» после первого символа.
   * Пустое поле: иногда scrollHeight сильно завышен — тогда держимся min-height из CSS.
   */
  function autoResize(textarea) {
    if (!textarea) return;
    const cs = getComputedStyle(textarea);
    const minH = parseFloat(cs.minHeight) || 0;
    const noChars = !textarea.value || textarea.value.length === 0;
    textarea.style.height = 'auto';
    const sh = textarea.scrollHeight;
    let target = Math.max(minH, sh);
    if (noChars && minH > 0 && sh > minH * 1.5) {
      target = minH;
    }
    textarea.style.height = target + 'px';
  }

  function bindAutoGrowTextarea(textarea) {
    if (!textarea || textarea.dataset.autoGrowBound === '1') return;
    textarea.dataset.autoGrowBound = '1';
    autoResize(textarea);
    textarea.addEventListener('input', () => {
      autoResize(textarea);
    });
    textarea.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      requestAnimationFrame(() => autoResize(textarea));
    });
  }

  function initAutosize() {
    document.querySelectorAll('textarea.auto-grow').forEach(bindAutoGrowTextarea);
  }


  // при обычной загрузке
  document.addEventListener('DOMContentLoaded', initAutosize);

  window.bindAutoGrowTextarea = bindAutoGrowTextarea;
  window.syncAutoGrowTextarea = autoResize;
})();



// static/js/reply_comment.js
(function () {
  'use strict';

  const getThreadContext = window.getThreadContext || function () {
    const marker = document.getElementById('threadViewMarker');
    if (!marker) return null;
    return {
      parentId: marker.dataset.parentId,
      backUrl: marker.dataset.backUrl,
    };
  };

  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))
      ?.split('=')[1];
  }

  async function parseJsonSafeReply(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  function closeAllReplyForms() {
    document.querySelectorAll('.reply-form').forEach(form => {
      form.classList.add('d-none');

      const textarea = form.querySelector('textarea[name="text"]');
      if (textarea) {
        textarea.value = '';
        textarea.style.removeProperty('height');
        delete textarea.dataset.mentionId;
      }

      form.querySelectorAll('.field-error').forEach((el) => el.remove());
      const errors = form.querySelector('.reply-form-errors');
      if (errors) {
        errors.textContent = '';
      }
    });

    document
      .querySelectorAll('.comment-active')
      .forEach(el => el.classList.remove('comment-active'));
  }
  window.closeAllReplyForms = closeAllReplyForms;

  function closeAllCommentEditForms() {
    document.querySelectorAll('.comment-edit-form .cancel-edit')
      .forEach(btn => btn.click());
  }
  window.closeAllCommentEditForms = closeAllCommentEditForms;

  function scrollReplyFormIntoView(container) {
    if (!container) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    requestAnimationFrame(() => {
      container.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'center',
        inline: 'nearest',
      });
    });
  }

  function openReplyForm(commentId, mentionId) {
    const container = document.getElementById(`reply-form-${commentId}`);
    if (!container) return;

    if (window.getReplyCooldownRemaining?.(commentId) > 0) return;

    if (window.closeAllCommentEditForms) {
      window.closeAllCommentEditForms();
    }
    closeAllReplyForms();
    container.classList.remove('d-none');

    const textarea = container.querySelector('textarea[name="text"]');
    if (!textarea) return;

    textarea.value = '';
    textarea.dataset.mentionId = mentionId;
    try {
      textarea.focus({ preventScroll: true });
    } catch {
      textarea.focus();
    }

    document.getElementById(`comment-${commentId}`)
      ?.classList.add('comment-active');

    scrollReplyFormIntoView(container);

    /* Reply изначально в d-none: первый bind мог измерить min-height как 0 — пересчитать после показа. */
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.syncAutoGrowTextarea?.(textarea);
      });
    });
  }

  function positionCommentMenuArrow() {
    /* Triangle ::before/::after on .comment-actions removed — keep hook for resize/menu open */
  }

  function closeAllCommentMenus() {
    document.querySelectorAll('.comment-menu.open').forEach(menu => {
      menu.classList.remove('open');
      menu.querySelector('.comment-menu-btn')?.setAttribute('aria-expanded', 'false');
    });
  }
  window.closeAllCommentMenus = closeAllCommentMenus;

  let _commentMenuResizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(_commentMenuResizeTimer);
    _commentMenuResizeTimer = setTimeout(() => {
      document.querySelectorAll('.comment-menu.open').forEach(positionCommentMenuArrow);
    }, 100);
  });

  window.addEventListener(
    'scroll',
    () => {
      if (document.querySelector('.comment-menu.open')) {
        closeAllCommentMenus();
      }
    },
    { passive: true, capture: true }
  );

  /* ===============================
     CLOSE FORMS ON OUTSIDE CLICK
  =============================== */
  document.addEventListener('click', (e) => {
    const clickedReplyForm = e.target.closest?.('.reply-form');
    const clickedEditForm = e.target.closest?.('.comment-edit-form');
    const replyTrigger = e.target.closest?.('.btn-reply, .comment-menu-action[data-action="reply"]');
    const editTrigger = e.target.closest?.('.btn-edit-comment');

    if (!clickedReplyForm && !replyTrigger) {
      closeAllReplyForms();
    }
    if (!clickedEditForm && !editTrigger) {
      closeAllCommentEditForms();
    }
  });

  function buildCommentShareUrl(commentId) {
    const base = window.location.href.split('#')[0];
    return `${base}#comment-anchor-${commentId}`;
  }

  function ensureShareOverlay() {
    let overlay = document.getElementById('commentShareOverlay');
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = 'commentShareOverlay';
    overlay.className = 'comment-share-overlay';
    overlay.innerHTML = '<div class="comment-share-overlay-text">Comment link copied to clipboard</div>';
    document.body.appendChild(overlay);
    return overlay;
  }

  function showShareOverlay() {
    const overlay = ensureShareOverlay();
    overlay.classList.add('is-visible');
    if (overlay.__timer) {
      clearTimeout(overlay.__timer);
    }
    overlay.__timer = setTimeout(() => {
      overlay.classList.remove('is-visible');
    }, 1400);
  }

  async function shareCommentUrl(url) {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(url);
        showShareOverlay();
        return;
      } catch { }
    }

    const temp = document.createElement('textarea');
    temp.value = url;
    temp.setAttribute('readonly', 'true');
    temp.style.position = 'absolute';
    temp.style.left = '-9999px';
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    showShareOverlay();
  }

  /* ===============================
     SHOW REPLY FORM
  =============================== */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-reply');
    if (!btn) return;

    e.preventDefault();

    const commentId = btn.dataset.commentId;
    const mentionId = btn.dataset.mentionId;
    if (window.getReplyCooldownRemaining?.(commentId) > 0) return;
    window.closeAllCommentMenus?.();
    openReplyForm(commentId, mentionId);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllCommentMenus();
  });

  /* ===============================
     COMMENT MENU
  =============================== */
  document.addEventListener('click', (e) => {
    const menuBtn = e.target.closest('.comment-menu-btn');
    if (menuBtn) {
      e.preventDefault();
      const menu = menuBtn.closest('.comment-menu');
      if (!menu) return;
      const wasOpen = menu.classList.contains('open');
      closeAllCommentMenus();
      if (!wasOpen) {
        menu.classList.add('open');
        menuBtn.setAttribute('aria-expanded', 'true');
        positionCommentMenuArrow(menu);
      }
      return;
    }

    const actionBtn = e.target.closest('.comment-menu-action');
    if (actionBtn) {
      if (actionBtn.classList.contains('disabled')) return;
      if (actionBtn.classList.contains('btn-delete-comment') || actionBtn.classList.contains('btn-edit-comment')) {
        closeAllCommentMenus();
        return;
      }
      if (actionBtn.tagName === 'A' && actionBtn.href) {
        closeAllCommentMenus();
        return;
      }
      e.preventDefault();
      const action = actionBtn.dataset.action;
      const commentId = actionBtn.dataset.commentId;
      const mentionId = actionBtn.dataset.mentionId;

      if (action === 'reply') {
        if (window.getReplyCooldownRemaining?.(commentId) > 0) return;
        openReplyForm(commentId, mentionId);
      } else if (action === 'share') {
        const url = buildCommentShareUrl(commentId);
        shareCommentUrl(url);
      } else if (action === 'report') {
        window.dispatchEvent(new CustomEvent('comment-report', { detail: { commentId } }));
      } else if (action === 'post-open-share') {
        window.dispatchEvent(new CustomEvent('open-post-share-modal', { detail: { trigger: actionBtn } }));
      } else if (action === 'post-report') {
        const postId = actionBtn.dataset.itemId;
        if (postId) {
          window.dispatchEvent(new CustomEvent('post-report', { detail: { postId } }));
        }
      }

      closeAllCommentMenus();
      return;
    }

    if (!e.target.closest('.comment-menu')) {
      closeAllCommentMenus();
    }
  });


  /* ===============================
     CANCEL REPLY
  =============================== */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.cancel-reply');
    if (!btn) return;

    const form = btn.closest('.reply-form');
    if (!form) return;

    // 🔥 скрываем форму
    form.classList.add('d-none');

    const textarea = form.querySelector('textarea[name="text"]');
    if (textarea) {
      textarea.value = '';
      delete textarea.dataset.mentionId;
      textarea.style.removeProperty('height');
    }

    form.querySelectorAll('.field-error').forEach((el) => el.remove());
    const errors = form.querySelector('.reply-form-errors');
    if (errors) {
      errors.textContent = '';
    }

    document
      .querySelectorAll('.comment-active')
      .forEach(el => el.classList.remove('comment-active'));
  });

  /* ===============================
     SUBMIT REPLY  🔥 КЛЮЧЕВОЙ БЛОК
  =============================== */
  document.addEventListener('submit', async (e) => {
    const form = e.target.closest('.reply-comment-form');
    if (!form) return;

    e.preventDefault();

    const textarea = form.querySelector('textarea[name="text"]');
    const errors = form.querySelector('.reply-form-errors');

    const parentId = form.dataset.parentId;
    const parentComment = document.getElementById('comment-' + parentId);
    if (!textarea || !parentComment) return;

    form.querySelectorAll('.field-error').forEach((el) => el.remove());
    if (errors) {
      errors.textContent = '';
    }

    const limitOk = window.enforceCommentLimit
      ? window.enforceCommentLimit(textarea)
      : true;
    if (!limitOk) {
      textarea.focus();
      return;
    }

    let text = textarea.value.trim();
    if (!text) {
      window.showCommentFieldError?.(textarea, 'Please write a reply...');
      return;
    }

    const mentionId = textarea.dataset.mentionId;
    if (mentionId) {
      text = `@[user:${mentionId}], ${text}`;
    }

    const trustStatusUrl = document.body.dataset.trustStatusUrl;
    if (trustStatusUrl) {
      try {
        const statusResp = await fetch(trustStatusUrl, {
          headers: { 'Accept': 'application/json' },
          credentials: 'same-origin'
        });
        if (statusResp.ok) {
          const statusData = await statusResp.json();
          if (statusData && statusData.shadow_banned) {
            if (errors) {
              errors.textContent =
                'You have been shadow banned. Improve your trust score to restore access.';
            }
            return;
          }
        }
      } catch (e) { /* ignore */ }
    }

    const fd = new FormData();
    fd.append('text', text);
    fd.append('parent_id', parentId);

    try {
      const replyContainer = form.closest('[data-reply-url]') || parentComment;
      const replyUrl = replyContainer?.dataset.replyUrl;
      if (!replyUrl) {
        if (errors) errors.textContent = 'Reply URL not found.';
        return;
      }
      const threadUrl =
        parentComment?.dataset?.threadUrl || defaultThreadUrl(parentId);

      const csrfToken =
        document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        getCookie('csrftoken') ||
        '';

      const resp = await fetch(replyUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: fd
      });

      const data = await parseJsonSafeReply(resp);
      if (!resp.ok || !data?.success) {
        if (errors) errors.textContent = data?.error || 'Server error.';
        return;
      }

      try {
        // ⬇️ ВСТАВКА REPLY
        const isThreadView = !!getThreadContext();
        const parentDepth = parseInt(parentComment.dataset.depth || '0', 10);
        if (!isThreadView && parentDepth >= 2) {
          // For deep replies, keep only the thread link on item page
          let link = document.getElementById('replies-thread-link-' + parentId);
          if (!link) {
            insertThreadLinkIntoParentMain(
              parentComment,
              parentId,
              buildThreadLink(parentId, threadUrl, 1)
            );
          } else {
            window.adjustThreadLinkCount?.(parentId, 1);
          }
          window.startReplyCooldown?.(parentId);
          closeAllReplyForms();
          return;
        }

        const main = parentComment.querySelector('.comment-main');
        let replies = main?.querySelector(`.replies[data-parent-id="${parentId}"]`);
        const hadBucket = !!replies;
        if (!replies) {
          replies = window.ensureRepliesBucketForAjax?.(parentComment, parentId, { initialCount: 1 });
        }
        if (!replies) {
          if (errors) errors.textContent = 'Render error.';
          return;
        }

        replies.insertAdjacentHTML('afterbegin', data.comment_html);
        if (hadBucket) window.bumpRepliesToggleCount?.(parentComment, parentId, 1);
        window.expandRepliesBucketForParent?.(parentComment, parentId);
        const insertedRoot = replies.firstElementChild?.classList?.contains('comment-block')
          ? replies.firstElementChild
          : replies.querySelector('.comment-block');
        if (insertedRoot) window.expandCommentThreadAncestors?.(insertedRoot);
        window.initCommentToggles?.(replies);
        window.initCommentLikes?.();
        window.initAllReplyButtonsCooldown?.();

        // if we're on thread page, ensure empty state cleared and link removal flag reset
        const threadContext = getThreadContext();
        if (threadContext) {
          const threadParentId = threadContext.parentId;
          if (threadParentId) {
            const threadEmpty = document.getElementById('threadEmpty');
            if (threadEmpty) threadEmpty.classList.add('d-none');
            try {
              sessionStorage.removeItem('thread_remove_link_' + threadParentId);
            } catch { }
            const threadRoot = document.getElementById('comment-' + threadParentId);
            const threadReplies = threadRoot?.querySelector('.replies');
            const replyCount = window.countDirectReplyBlocks
              ? window.countDirectReplyBlocks(threadReplies)
              : 0;
            try {
              sessionStorage.setItem('thread_replies_count_' + threadParentId, String(replyCount));
            } catch { }
          }
        }

        window.startReplyCooldown?.(parentId);
        closeAllReplyForms();
      } catch (renderErr) {
        if (errors) errors.textContent = 'Render error.';
      }
    } catch (err) {
      if (errors) errors.textContent = 'Unable to submit. Please try again.';
    }
  });

  window.initAllReplyButtonsCooldown?.();

})();



//@mention listing
(function () {
  'use strict';
  let scrollTimer = null;

  function ensureCommentVisible(commentId) {
    const target = document.getElementById(`comment-${commentId}`);
    if (!target) return false;
    window.expandCommentThreadAncestors?.(target);
    return true;
  }
  window.ensureCommentVisible = ensureCommentVisible;
  window.ensureRootCommentVisible = ensureCommentVisible;

  document.addEventListener('click', (e) => {
    const link = e.target.closest('.mention-link');
    if (!link) return;

    e.preventDefault();
    e.stopImmediatePropagation();

    const commentId = link.dataset.parentId;
    ensureCommentVisible(commentId);
    const comment = document.getElementById(`comment-${commentId}`);
    if (!comment) {
      return;
    }

    const rect = comment.getBoundingClientRect();
    const vh = window.innerHeight || document.documentElement.clientHeight;

    const header = document.querySelector('header.header') || document.querySelector('.header');
    const headerH = header ? Math.ceil(header.getBoundingClientRect().height || 0) : 0;
    const SAFE_GAP = 12;

    /* ===============================
       НАСТРОЙКИ ОБЗОРА
    =============================== */
    const VIEW_TOP_OFFSET = headerH + SAFE_GAP;   // 👈 ЗОНА ОБЗОРА СВЕРХУ
    const VIEW_BOTTOM_OFFSET = 100; // 👈 снизу
    const SCROLL_OFFSET = headerH + SAFE_GAP;     // 👈 куда реально скроллим

    const isVisible =
      rect.top >= VIEW_TOP_OFFSET &&
      rect.bottom <= vh - VIEW_BOTTOM_OFFSET;

    // ✅ если уже в зоне видимости — только подсветка + bounce
    if (isVisible) {
      if (scrollTimer) {
        clearTimeout(scrollTimer);
        scrollTimer = null;
      }
      highlightComment(comment);
      return;
    }

    // 🔥 скроллим ЧУТЬ ВЫШЕ комментария
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const targetY = rect.top + scrollTop - SCROLL_OFFSET;

    window.scrollTo({
      top: targetY,
      behavior: 'auto'
    });

    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      highlightComment(comment);
      scrollTimer = null;
    }, 300);
  });

  function highlightComment(comment) {
    const text = comment.querySelector('.comment-text');
    if (!text) return;

    // снять со всех
    document
      .querySelectorAll('.comment-text.root-mention-highlight')
      .forEach(el => el.classList.remove('root-mention-highlight'));

    // перезапуск анимации без ожидания завершения предыдущей
    text.classList.remove('root-mention-highlight');
    void text.offsetWidth; // 🔥 принудительный reflow
    text.classList.add('root-mention-highlight');
  }

  function highlightCommentFromHash() {
    const hash = window.location.hash || '';
    if (!hash.startsWith('#comment-anchor-')) return;
    const id = hash.replace('#comment-anchor-', '').trim();
    if (!id) return;
    ensureCommentVisible(id);
    const comment = document.getElementById(`comment-${id}`);
    if (!comment) return;
    setTimeout(() => highlightComment(comment), 120);
  }

  window.highlightCommentFromHash = highlightCommentFromHash;
  window.addEventListener('hashchange', highlightCommentFromHash);
  document.addEventListener('DOMContentLoaded', () => {
    highlightCommentFromHash();
  });
})();


// Short annotation
function buildShortHTML(fullHTML, maxLen = 400) {
  const tmp = document.createElement('div');
  tmp.innerHTML = fullHTML;

  let count = 0;

  function walk(node) {
    if (count >= maxLen) {
      node.remove();
      return;
    }

    if (node.nodeType === Node.TEXT_NODE) {
      const remaining = maxLen - count;

      if (node.textContent.length > remaining) {
        node.textContent = node.textContent.slice(0, remaining) + '…';
        count = maxLen;
      } else {
        count += node.textContent.length;
      }
      return;
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      Array.from(node.childNodes).forEach(walk);

      // если элемент стал пустым — удалить
      if (!node.textContent.trim()) {
        node.remove();
      }
    }
  }

  Array.from(tmp.childNodes).forEach(walk);
  return tmp.innerHTML;
}


// comments-toggle.js (MENTION-SAFE)
(function () {
  function initCommentToggles(root = document) {
    root.querySelectorAll('.comment-text').forEach(textEl => {
      if (textEl.dataset.toggleInit) return;

      if (textEl.textContent.trim().length <= 350) return;

      textEl.dataset.fullHtml ||= textEl.innerHTML;

      const btn = document.createElement('button');
      btn.className = 'comment-toggle-btn';
      btn.textContent = 'Show more';

      let expanded = false;

      function render() {
        textEl.innerHTML = expanded
          ? textEl.dataset.fullHtml
          : buildShortHTML(textEl.dataset.fullHtml, 350);

        btn.textContent = expanded ? 'Show less' : 'Show more';
        textEl.classList.toggle('comment-text--truncated', !expanded);
      }

      btn.addEventListener('click', () => {
        expanded = !expanded;
        render();
      });

      render();
      textEl.after(btn);
      textEl.dataset.toggleInit = '1';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initCommentToggles();
  });

  window.initCommentToggles = initCommentToggles;
})();


