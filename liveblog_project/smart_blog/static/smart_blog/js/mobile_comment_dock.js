// static/js/mobile_comment_dock.js
//
// Mobile-only YouTube-style fixed-bottom comment composer.
// Renders only for authenticated users (template gating). Handles three modes:
//   - "comment": top-level comment (default)
//   - "reply":   reply to a specific comment (X button cancels back to comment)
//   - "edit":    edit one of the current user's own comments
//
// Send button (paper-plane) is enabled ONLY when the textarea has non-blank text.
// When the per-user/per-item add-comment cooldown is active, the send button
// shows a red countdown (30s); the textarea stays editable. Draft syncs 1:1
// with the desktop #commentForm and must never be overwritten on cooldown end.
(function () {
  'use strict';

  const dock = document.getElementById('mobileCommentDock');
  if (!dock) return;

  document.body.classList.add('has-mobile-comment-dock');
  dock.removeAttribute('hidden');

  let dockRevealed = false;
  let scrollRevealBound = false;

  const form = dock.querySelector('.mobile-comment-dock__form');
  const field = dock.querySelector('.mobile-comment-dock__field');
  const textarea = dock.querySelector('.mobile-comment-dock__textarea');
  const sendBtn = dock.querySelector('.mobile-comment-dock__send');
  const closeBtn = dock.querySelector('.mobile-comment-dock__close');

  const itemId = dock.dataset.itemId;
  const userId = dock.dataset.userId;
  const addUrl = dock.dataset.addUrl;
  const trustStatusUrl = dock.dataset.trustStatusUrl;

  const CSRF =
    form.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] ||
    '';

  /* ===============================================
     State
  =============================================== */
  // mode: 'comment' | 'reply' | 'edit'
  let mode = 'comment';
  let replyContext = null; // { parentId, mentionId, replyUrl, threadUrl }
  let editContext = null;  // { commentNode, commentId, editUrl, mention, mentionId }
  let cooldownTimer = null;
  const SEND_ICON_HTML =
    '<i class="fa fa-paper-plane-o" aria-hidden="true"></i>';

  /* ===============================================
     Helpers
  =============================================== */
  function isMobile() {
    return window.matchMedia('(max-width: 767.98px)').matches;
  }

  function isThreadCommentPage() {
    return document.body.classList.contains('thread-comment-page');
  }

  /** Item detail: whole comments block (stays “active” while reading the list). */
  function getCommentsRevealTarget() {
    const section = document.getElementById('detailCommentsSection');
    if (section && !section.hasAttribute('hidden')) return section;
    return document.getElementById('detailCommentsEmpty');
  }

  function shouldRevealDockFromScroll() {
    if (!isMobile()) return false;
    if (isThreadCommentPage()) return true;
    const target = getCommentsRevealTarget();
    if (!target) return false;
    const rect = target.getBoundingClientRect();
    /* Not reached comments yet (block still below the fold). */
    if (rect.top > window.innerHeight) return false;
    /* Scrolled back above the whole comments block. */
    if (rect.bottom < 0) return false;
    return true;
  }

  function setDockRevealed(reveal) {
    if (reveal === dockRevealed) return;
    dockRevealed = reveal;
    dock.classList.toggle('is-revealed', reveal);
    document.body.classList.toggle('is-dock-revealed', reveal);
  }

  function updateDockRevealFromScroll() {
    if (!isMobile()) {
      setDockRevealed(false);
      return;
    }
    setDockRevealed(shouldRevealDockFromScroll());
  }

  function bindDockScrollReveal() {
    if (scrollRevealBound) return;
    scrollRevealBound = true;
    let ticking = false;
    const onScrollOrResize = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        updateDockRevealFromScroll();
      });
    };
    window.addEventListener('scroll', onScrollOrResize, { passive: true });
    window.addEventListener('resize', onScrollOrResize, { passive: true });
  }

  /** Smooth scroll so the new comment sits above the dock (mobile only). */
  function scrollToInsertedComment(insertRoot) {
    if (!isMobile() || !insertRoot) return;
    const run = () => {
      const node =
        insertRoot.classList?.contains('comment-block')
          ? insertRoot
          : insertRoot.querySelector?.('.comment-block') || insertRoot;
      if (!node || !node.getBoundingClientRect) return;
      const dockH = dock.offsetHeight || 72;
      const top =
        node.getBoundingClientRect().top + window.scrollY - 12 - dockH;
      const reduceMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      ).matches;
      window.scrollTo({
        top: Math.max(0, top),
        behavior: reduceMotion ? 'auto' : 'smooth',
      });
    };
    requestAnimationFrame(() => requestAnimationFrame(run));
  }

  function getCommentCooldown() {
    if (typeof window.getCommentCooldownRemaining === 'function') {
      return window.getCommentCooldownRemaining(itemId, userId);
    }
    return 0;
  }

  function setSendEnabled() {
    if (!sendBtn) return;
    const hasText = textarea.value.trim().length > 0;
    if (mode !== 'comment') {
      sendBtn.disabled = !hasText;
      return;
    }
    if (getCommentCooldown() > 0 || sendBtn.classList.contains('is-cooldown')) {
      sendBtn.disabled = true;
      return;
    }
    sendBtn.disabled = !hasText;
  }

  /* Auto-grow up to 10 rows; the field wrapper scrolls internally so the
     scrollbar stays inside the textarea column and never overlaps buttons. */
  function autoGrow() {
    if (!textarea || !field) return;
    if (textarea.offsetParent === null) return;

    textarea.style.height = 'auto';
    field.classList.remove('is-scrollable');
    field.scrollTop = 0;

    const maxH = parseFloat(getComputedStyle(field).maxHeight);
    const scrollH = textarea.scrollHeight;

    if (scrollH > 0) {
      textarea.style.height = scrollH + 'px';
    }

    if (Number.isFinite(maxH) && maxH > 0 && scrollH > maxH + 1) {
      field.classList.add('is-scrollable');
    }
  }

  /* --- Bi-directional sync with the desktop main comment textarea ---
     When the viewport flips between mobile and desktop, the user expects
     to see the same draft text in both composers. Only sync in `comment`
     mode at all times (including during send-button cooldown). */
  function getDesktopTextarea() {
    return document.querySelector('#commentForm textarea[name="text"]');
  }

  let syncingFromDesktop = false;
  let syncingFromDock = false;

  /** Re-measure desktop #commentForm textarea after it becomes visible.
   *  While the form is display:none (mobile layout), auto-grow reads a wrong
   *  scrollHeight and can leave a one-line inline height — fix on resize. */
  function scheduleDesktopTextareaGrow(main) {
    main = main || getDesktopTextarea();
    if (!main || isMobile()) return;
    if (typeof window.bindAutoGrowTextarea === 'function') {
      window.bindAutoGrowTextarea(main);
    }
    const run = () => {
      if (typeof window.syncAutoGrowTextarea === 'function') {
        window.syncAutoGrowTextarea(main);
      }
    };
    requestAnimationFrame(() => requestAnimationFrame(run));
  }

  function syncDockToDesktop() {
    if (mode !== 'comment') return;
    const main = getDesktopTextarea();
    if (!main) return;

    const dockVal = textarea.value;
    const changed = main.value !== dockVal;
    if (changed) {
      syncingFromDock = true;
      main.value = dockVal;
      /* Do not fire input while the desktop form is hidden — autosize would
         measure scrollHeight as ~1 line and stick that height until resize. */
      if (!isMobile()) {
        try {
          main.dispatchEvent(new Event('input', { bubbles: true }));
        } catch (e) { /* ignore */ }
      }
      syncingFromDock = false;
    }

    if (!isMobile()) {
      scheduleDesktopTextareaGrow(main);
    }
  }

  function syncDesktopToDock() {
    if (mode !== 'comment') return;
    const main = getDesktopTextarea();
    if (!main) return;
    if (main.value === textarea.value) return;
    syncingFromDesktop = true;
    textarea.value = main.value;
    autoGrow();
    setSendEnabled();
    syncingFromDesktop = false;
  }

  /** Refresh desktop-only UI (CLR button, autosize) after dock→desktop sync. */
  function refreshDesktopCommentFormUI() {
    const main = getDesktopTextarea();
    if (!main || isMobile()) return;
    try {
      main.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (e) { /* ignore */ }
    scheduleDesktopTextareaGrow(main);
  }

  /** Keep draft 1:1 and fix desktop textarea height after viewport change. */
  function syncComposersForViewport() {
    if (mode !== 'comment') return;
    if (isMobile()) {
      syncDesktopToDock();
      autoGrow();
      setSendEnabled();
    } else {
      syncDockToDesktop();
      refreshDesktopCommentFormUI();
    }
  }

  function attachDesktopSync() {
    const main = getDesktopTextarea();
    if (!main || main.__mobileDockSyncBound) return;
    main.__mobileDockSyncBound = true;
    main.addEventListener('input', () => {
      if (syncingFromDock) return;
      syncDesktopToDock();
    });
  }

  function showError(message) {
    if (!message) {
      const existing = dock.querySelector('.mobile-comment-dock__error');
      if (existing) existing.remove();
      return;
    }
    let bucket = dock.querySelector('.mobile-comment-dock__error');
    if (!bucket) {
      bucket = document.createElement('div');
      bucket.className = 'mobile-comment-dock__error';
      dock.appendChild(bucket);
    }
    bucket.textContent = message;
    bucket.removeAttribute('hidden');
    clearTimeout(showError.__timer);
    showError.__timer = setTimeout(() => {
      bucket?.remove();
    }, 4500);
  }

  /* ===============================================
     Cooldown UI on send button (textarea stays editable)
  =============================================== */
  function renderSendCooldown(remaining) {
    if (!sendBtn) return;
    sendBtn.classList.add('is-cooldown');
    sendBtn.disabled = true;
    sendBtn.setAttribute('aria-label', `Please wait ${remaining} seconds`);
    sendBtn.textContent = String(remaining);
  }

  function renderSendNormal() {
    if (!sendBtn) return;
    sendBtn.classList.remove('is-cooldown');
    sendBtn.innerHTML = SEND_ICON_HTML;
    sendBtn.setAttribute('aria-label', 'Send');
    setSendEnabled();
  }

  function stopCooldownTimer() {
    if (cooldownTimer) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }

  function applySendCooldownUI() {
    if (mode !== 'comment') {
      stopCooldownTimer();
      return;
    }
    const remaining = getCommentCooldown();
    if (remaining > 0) {
      renderSendCooldown(remaining);
      if (!cooldownTimer) {
        cooldownTimer = setInterval(applySendCooldownUI, 1000);
      }
      return;
    }
    stopCooldownTimer();
    renderSendNormal();
  }

  function ensureCooldownPolling() {
    if (mode !== 'comment') {
      stopCooldownTimer();
      return;
    }
    applySendCooldownUI();
  }

  /* ===============================================
     Mode switching
  =============================================== */
  function resetTextarea() {
    textarea.value = '';
    if (field) field.scrollTop = 0;
    autoGrow();
  }

  function setMode(nextMode, opts) {
    opts = opts || {};
    mode = nextMode;
    dock.dataset.mode = nextMode;
    showError('');
    updateDockRevealFromScroll();

    if (nextMode === 'comment') {
      replyContext = null;
      editContext = null;
      closeBtn.setAttribute('hidden', '');
      textarea.placeholder = 'Comment…';
      document
        .querySelectorAll('.comment-active')
        .forEach(el => el.classList.remove('comment-active'));
      if (!opts.keepText) resetTextarea();
      // Pull the current desktop draft so user sees the same text when
      // returning to comment mode from reply/edit or from desktop view.
      syncDesktopToDock();
      ensureCooldownPolling();
      setSendEnabled();
      autoGrow();
      if (!isMobile()) {
        scheduleDesktopTextareaGrow();
      }
      return;
    }

    closeBtn.removeAttribute('hidden');
    /* Reply/edit use the same send control — hide main-comment cooldown UI. */
    stopCooldownTimer();
    sendBtn.classList.remove('is-cooldown');
    sendBtn.innerHTML = SEND_ICON_HTML;
    sendBtn.setAttribute('aria-label', 'Send');

    if (nextMode === 'reply') {
      textarea.placeholder = 'Write a reply…';
      if (!opts.keepText) {
        textarea.value = '';
      }
    } else if (nextMode === 'edit') {
      textarea.placeholder = 'Edit your comment…';
    }

    setSendEnabled();
  }

  /* ===============================================
     Public openers (called from comment_operate.js)
   =============================================== */
  window.openMobileDockReply = function (commentId, mentionId) {
    if (!isMobile()) return;
    const parentComment = document.getElementById('comment-' + commentId);
    if (!parentComment) return;

    if (window.getReplyCooldownRemaining?.(commentId) > 0) return;

    const replyContainer = parentComment.closest?.('[data-reply-url]') || parentComment;
    const replyUrl = replyContainer?.dataset?.replyUrl;
    const threadUrl = parentComment?.dataset?.threadUrl;

    replyContext = {
      parentId: String(commentId),
      mentionId: mentionId ? String(mentionId) : '',
      replyUrl,
      threadUrl,
    };

    setMode('reply');

    document
      .querySelectorAll('.comment-active')
      .forEach(el => el.classList.remove('comment-active'));
    parentComment.classList.add('comment-active');

    requestAnimationFrame(() => {
      try {
        textarea.focus({ preventScroll: false });
      } catch (e) {
        textarea.focus();
      }
    });
  };

  window.openMobileDockEdit = function (commentNode, commentId, editUrl) {
    if (!isMobile()) return;
    if (!commentNode || !editUrl) return;

    const payload = window.extractCommentEditPayload
      ? window.extractCommentEditPayload(commentNode)
      : { text: '', mention: '', mentionId: '' };

    editContext = {
      commentNode,
      commentId: String(commentId),
      editUrl,
      mention: payload.mention || '',
      mentionId: payload.mentionId || '',
    };

    setMode('edit', { keepText: true });
    textarea.value = payload.text || '';
    autoGrow();
    setSendEnabled();

    requestAnimationFrame(() => {
      try {
        textarea.focus({ preventScroll: false });
        const len = textarea.value.length;
        textarea.setSelectionRange(len, len);
      } catch (e) { /* ignore */ }
    });
  };

  /* ===============================================
     Event wiring
  =============================================== */
  const COMMENT_MAX_CHARS = 1500;
  function exceedsLimit() {
    return String(textarea.value || '').replace(/\r?\n/g, '').length > COMMENT_MAX_CHARS;
  }

  textarea.addEventListener('input', () => {
    autoGrow();
    setSendEnabled();
    if (exceedsLimit()) {
      showError(`Maximum ${COMMENT_MAX_CHARS} characters (line breaks are not counted).`);
      sendBtn.disabled = true;
    }
    if (!syncingFromDesktop) syncDockToDesktop();
  });

  closeBtn.addEventListener('click', (e) => {
    e.preventDefault();
    setMode('comment');
    try {
      textarea.blur();
    } catch (err) { /* ignore */ }
  });

  /* ===============================================
     Submit
  =============================================== */
  async function checkShadowBan() {
    if (!trustStatusUrl) return false;
    try {
      const resp = await fetch(trustStatusUrl, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      if (!resp.ok) return false;
      const data = await resp.json().catch(() => null);
      return !!(data && data.shadow_banned);
    } catch (e) {
      return false;
    }
  }

  function safeJson(resp) {
    return resp.json().catch(() => null);
  }

  async function submitComment() {
    if (getCommentCooldown() > 0) {
      applySendCooldownUI();
      return;
    }
    const text = textarea.value.trim();
    if (!text) return;

    sendBtn.disabled = true;

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('text', text);

    try {
      const resp = await fetch(addUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': CSRF,
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        body: fd,
      });

      const data = await safeJson(resp);
      if (resp.ok && data?.success) {
        const list =
          document.getElementById('commentsListPreview') ||
          document.getElementById('commentsList');
        let insertedRoot = null;
        if (list && data.comment_html) {
          list.insertAdjacentHTML('afterbegin', data.comment_html);
          insertedRoot = list.firstElementChild;
          // detail preview trimming: replicate desktop behaviour
          const preview = document.getElementById('commentsListPreview');
          if (preview && list === preview) {
            const max = parseInt(preview.dataset.previewLimit || '10', 10) || 10;
            const roots = preview.querySelectorAll(':scope > .comment-block');
            for (let i = max; i < roots.length; i++) roots[i].remove();
            insertedRoot = preview.firstElementChild;
          }
          if (insertedRoot) {
            window.initCommentToggles?.(insertedRoot);
            window.initCommentLikes?.();
          }
        }
        const count = data.comments_count;
        applyCounterUpdates(count);
        if (insertedRoot) {
          scrollToInsertedComment(insertedRoot);
        }

        if (typeof window.startCommentCooldown === 'function') {
          window.startCommentCooldown(
            itemId,
            null,
            window.COMMENT_COOLDOWN_SEC || 30,
            userId
          );
        }
        textarea.value = '';
        if (field) field.scrollTop = 0;
        autoGrow();
        // Clear desktop textarea too (and trigger its own input handlers so
        // any clear-button / char-counter UI updates).
        const main = getDesktopTextarea();
        if (main && main.value) {
          syncingFromDock = true;
          main.value = '';
          try {
            main.dispatchEvent(new Event('input', { bubbles: true }));
          } catch (e) { /* ignore */ }
          main.style.removeProperty('height');
          syncingFromDock = false;
        }
        applySendCooldownUI();
        return;
      }

      if (resp.status === 429) {
        const seconds = window.parseCommentCooldownSeconds
          ? window.parseCommentCooldownSeconds(data?.error)
          : null;
        if (seconds && typeof window.startCommentCooldown === 'function') {
          window.startCommentCooldown(itemId, null, seconds, userId);
          applySendCooldownUI();
          return;
        }
      }

      showError(data?.error || 'Unable to submit. Please try again.');
    } catch (err) {
      showError('Unable to submit. Please try again.');
    } finally {
      setSendEnabled();
    }
  }

  function applyCounterUpdates(count) {
    if (count == null) return;
    const human = (n) => {
      n = Number(n);
      if (n < 1000) return String(n);
      if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
      if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
      if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
      return String(n);
    };
    const txt = human(count);
    const el = document.getElementById('commentsCount');
    if (el) el.textContent = txt;
    document.querySelectorAll('.js-item-detail-comments-count').forEach(node => {
      node.textContent = txt;
    });
    const cardLikes = document.getElementById('comments-count-' + itemId);
    if (cardLikes) cardLikes.textContent = txt;

    const section = document.getElementById('detailCommentsSection');
    const emptyEl = document.getElementById('detailCommentsEmpty');
    if (section) {
      if (count > 0) section.removeAttribute('hidden');
      else section.setAttribute('hidden', '');
    }
    if (emptyEl) {
      if (count > 0) emptyEl.setAttribute('hidden', '');
      else emptyEl.removeAttribute('hidden');
    }
    const readWrap = document.getElementById('detailCommentsReadMoreWrap');
    const preview = document.getElementById('commentsListPreview');
    if (readWrap && preview) {
      const th = parseInt(preview.dataset.previewLimit || '10', 10) || 10;
      if (count > th) readWrap.removeAttribute('hidden');
      else readWrap.setAttribute('hidden', '');
    }

    try {
      const key = 'listing_changes';
      const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
      if (itemId) {
        changes[itemId] = changes[itemId] || {};
        changes[itemId].comments_count = count;
        sessionStorage.setItem(key, JSON.stringify(changes));
      }
    } catch (e) { /* ignore */ }
  }

  async function submitReply() {
    if (!replyContext) return;
    let text = textarea.value.trim();
    if (!text) return;

    if (await checkShadowBan()) {
      showError('You have been shadow banned. Improve your trust score to restore access.');
      return;
    }

    if (replyContext.mentionId) {
      text = `@[user:${replyContext.mentionId}], ${text}`;
    }

    sendBtn.disabled = true;

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('text', text);
    fd.append('parent_id', replyContext.parentId);

    try {
      const resp = await fetch(replyContext.replyUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': CSRF,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: fd,
      });
      const data = await safeJson(resp);
      if (!resp.ok || !data?.success) {
        showError(data?.error || 'Server error.');
        return;
      }

      const parentId = replyContext.parentId;
      const parentComment = document.getElementById('comment-' + parentId);
      if (!parentComment) {
        showError('Render error.');
        return;
      }

      const threadCtx = window.getThreadContext?.();
      const isThreadView = !!threadCtx;
      const parentDepth = parseInt(parentComment.dataset.depth || '0', 10);

      if (!isThreadView && parentDepth >= 2) {
        let link = document.getElementById('replies-thread-link-' + parentId);
        if (!link) {
          if (window.insertThreadLinkIntoParentMain && window.buildThreadLink) {
            window.insertThreadLinkIntoParentMain(
              parentComment,
              parentId,
              window.buildThreadLink(parentId, replyContext.threadUrl || '#', 1)
            );
          }
        } else {
          window.adjustThreadLinkCount?.(parentId, 1);
        }
        window.startReplyCooldown?.(parentId);
        setMode('comment');
        return;
      }

      const main = parentComment.querySelector('.comment-main');
      let replies = main?.querySelector(`.replies[data-parent-id="${parentId}"]`);
      const hadBucket = !!replies;
      if (!replies && typeof window.ensureRepliesBucketForAjax === 'function') {
        replies = window.ensureRepliesBucketForAjax(parentComment, parentId, { initialCount: 1 });
      }
      if (!replies) {
        showError('Render error.');
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

      if (isThreadView && threadCtx?.parentId) {
        const tpid = threadCtx.parentId;
        const threadEmpty = document.getElementById('threadEmpty');
        if (threadEmpty) threadEmpty.classList.add('d-none');
        try {
          sessionStorage.removeItem('thread_remove_link_' + tpid);
          const threadRoot = document.getElementById('comment-' + tpid);
          const threadReplies = threadRoot?.querySelector('.replies');
          const rc = window.countDirectReplyBlocks
            ? window.countDirectReplyBlocks(threadReplies)
            : 0;
          sessionStorage.setItem('thread_replies_count_' + tpid, String(rc));
        } catch (e) { /* ignore */ }
      }

      window.startReplyCooldown?.(parentId);
      if (insertedRoot) {
        scrollToInsertedComment(insertedRoot);
      }
      setMode('comment');
      try { textarea.blur(); } catch (e) { /* ignore */ }
    } catch (err) {
      showError('Unable to submit. Please try again.');
    } finally {
      setSendEnabled();
    }
  }

  async function submitEdit() {
    if (!editContext) return;
    let text = textarea.value.trim();
    if (!text) return;

    if (await checkShadowBan()) {
      showError('You have been shadow banned. Improve your trust score to restore access.');
      return;
    }

    const { commentNode, commentId, editUrl, mention, mentionId } = editContext;
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

    sendBtn.disabled = true;

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('text', text);

    try {
      const resp = await fetch(editUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': CSRF,
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        body: fd,
      });
      const data = await safeJson(resp);
      if (!resp.ok || !data?.success) {
        showError(data?.errors?.text?.[0] || data?.error || 'Server error.');
        return;
      }
      let newNode = null;
      if (typeof window.swapEditedCommentNode === 'function') {
        newNode = window.swapEditedCommentNode(commentNode, data.comment_html);
      }
      if (newNode) {
        window.restoreCommentUI?.(newNode);
        window.initCommentLikes?.();
        window.initAutoDismiss?.(newNode);
      }
      setMode('comment');
      try { textarea.blur(); } catch (e) { /* ignore */ }
    } catch (err) {
      showError('Unable to save. Please try again.');
    } finally {
      setSendEnabled();
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (sendBtn.disabled) return;
    if (exceedsLimit()) {
      showError(`Maximum ${COMMENT_MAX_CHARS} characters (line breaks are not counted).`);
      return;
    }
    if (mode === 'reply') {
      submitReply();
    } else if (mode === 'edit') {
      submitEdit();
    } else {
      submitComment();
    }
  });

  /* External signals */
  window.addEventListener('comment-cooldown-started', () => {
    if (mode !== 'comment') return;
    syncDesktopToDock();
    applySendCooldownUI();
  });

  window.addEventListener('comment-cooldown-ended', () => {
    if (mode !== 'comment') return;
    syncDesktopToDock();
    applySendCooldownUI();
  });

  // Viewport flip: same draft in both composers + correct textarea height.
  let _resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(() => {
      if (!isMobile() && mode !== 'comment') {
        setMode('comment');
      }
      syncComposersForViewport();
      updateDockRevealFromScroll();
    }, 50);
  });

  /* matchMedia is more reliable than resize alone when DevTools toggles layout */
  const mobileMq = window.matchMedia('(max-width: 767.98px)');
  if (typeof mobileMq.addEventListener === 'function') {
    mobileMq.addEventListener('change', () => {
      if (!isMobile() && mode !== 'comment') {
        setMode('comment');
      }
      syncComposersForViewport();
      updateDockRevealFromScroll();
    });
  } else if (typeof mobileMq.addListener === 'function') {
    mobileMq.addListener(() => {
      if (!isMobile() && mode !== 'comment') {
        setMode('comment');
      }
      syncComposersForViewport();
      updateDockRevealFromScroll();
    });
  }

  // Init
  bindDockScrollReveal();
  setMode('comment');
  applySendCooldownUI();
  attachDesktopSync();
  // Pull any existing desktop draft on first load so the dock isn't empty
  // when user typed on desktop, resized to mobile, then opened the page.
  syncDesktopToDock();
  setSendEnabled();
  autoGrow();
  updateDockRevealFromScroll();
})();
