(function () {
  'use strict';

  const stackTrigger = document.getElementById('likedUsersStackTrigger') || document.querySelector('.liked-users-stack');
  const noLikesYet = document.getElementById('noLikesYet');
  const likedUsersContainer = document.getElementById('likedUsersContainer');
  const overlay = document.getElementById('likedUsersOverlay');
  const closeBtn = document.getElementById('likedUsersClose');
  const backdrop = overlay?.querySelector('.liked-users-backdrop');
  const stack = document.querySelector('.liked-users-stack');
  const list = overlay?.querySelector('.liked-users-list');
  const searchBtn = overlay?.querySelector('.users-search-btn');
  const searchIcon = searchBtn?.querySelector('.users-search-icon, i');
  const searchInput = overlay?.querySelector('.liked-users-search-input');
  const emptyMsg = overlay?.querySelector('.liked-users-empty-msg');
  const searchWrap = overlay?.querySelector('.liked-users-search-wrap');
  const container = overlay?.querySelector('.liked-users-list-container');
  const current = document.getElementById('likedUsersCurrent');
  /** Высота окна — под столько рядов; если лайков больше — скролл внутри списка */
  const MAX_VISIBLE = 10;
  const SEARCH_MIN_USERS = 6;
  let initialOrder = [];
  let searchActiveWithMany = false; /* true when search open and count >= 6 */
  if (!overlay) return;

  function getLikedCount() {
    if (!list) return 0;
    return list.querySelectorAll('.liked-users-item').length;
  }

  function captureInitialOrder() {
    if (!list) return;
    initialOrder = Array.from(list.querySelectorAll('.liked-users-item'));
  }

  function restoreInitialOrder() {
    if (!list || !initialOrder.length) return;
    initialOrder.forEach(function (item) {
      list.appendChild(item);
    });
  }

  function measureItemHeight() {
    if (!list) return { itemHeight: 0, gap: 0 };
    const sample = list.querySelector('.liked-users-item');
    if (!sample) return { itemHeight: 0, gap: 0 };
    const styles = window.getComputedStyle(list);
    const gap = parseFloat(styles.rowGap || styles.gap || 0) || 0;
    const itemHeight = sample.getBoundingClientRect().height || 0;
    return { itemHeight, gap };
  }

  const EMPTY_STATE_HEIGHT = 280;

  function getContainerMaxHeight() {
    if (!container) return 400;
    const panel = container.closest('.liked-users-panel');
    if (!panel) return 400;
    const header = panel.querySelector('.liked-users-header');
    const headerH = header ? header.getBoundingClientRect().height + 1 : 50;
    const hrH = 1;
    return Math.floor(Math.min(window.innerHeight * 0.8 - headerH - hrH - 40, 600));
  }

  function isEmptyStateActive() {
    return emptyMsg && emptyMsg.style.display !== 'none' && list && list.style.display === 'none';
  }

  function updateModalHeight(count, forceSearchLock, isEmptyState) {
    if (isEmptyState === undefined) isEmptyState = isEmptyStateActive();
    if (!container || !list) return;
    const lock = forceSearchLock || (searchActiveWithMany && count >= SEARCH_MIN_USERS);
    let { itemHeight, gap } = measureItemHeight();
    if (!itemHeight) {
      itemHeight = 50;
      gap = 10;
    }
    const paddingBottom = 16;
    let h;
    if (isEmptyState) {
      h = EMPTY_STATE_HEIGHT;
    } else {
      const n = Math.min(count, MAX_VISIBLE);
      h = Math.round(itemHeight * n + gap * Math.max(0, n - 1) + paddingBottom);
      if (lock) {
        const minH = Math.round(itemHeight * SEARCH_MIN_USERS + gap * (SEARCH_MIN_USERS - 1) + paddingBottom);
        h = Math.max(h, minH);
      }
    }
    const maxH = getContainerMaxHeight();
    h = Math.min(h, maxH);
    container.style.minHeight = h + 'px';
    container.style.maxHeight = h + 'px';
    list.style.minHeight = h + 'px';
    list.style.maxHeight = h + 'px';
    /* Всегда auto: иначе при «visible» + overflow:hidden у панели контент обрезается без скролла;
       расчёт h по одному sample-ряду часто занижает суммарную высоту; при resize (DevTools) то же. */
    list.style.overflowY = 'auto';
  }

  function updateSearchWrapVisibility(count) {
    if (!searchWrap) return;
    searchWrap.style.display = count > 50 ? '' : 'none';
  }

  function openOverlay() {
    captureInitialOrder();
    const count = getLikedCount();
    updateSearchWrapVisibility(count);
    filterLikedUsers(searchInput?.value || '');
    searchActiveWithMany = false;
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
    lockScroll();
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        updateModalHeight(count, false);
      });
    });
  }

  function closeOverlay() {
    if (overlay.classList.contains('hidden')) {
      return;
    }
    if (overlay.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    if (searchInput && searchInput.style.display !== 'none') {
      searchInput.style.display = 'none';
      searchInput.value = '';
      filterLikedUsers('');
      setSearchIcon(false);
    }
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
    unlockScroll();
    requestAnimationFrame(function () {
      try {
        stackTrigger?.focus({ preventScroll: true });
      } catch (err) {
        try { stackTrigger?.focus(); } catch (e2) { /* ignore */ }
      }
    });
  }

  function openOnClick(e) {
    e.preventDefault();
    if (!likedUsersContainer || likedUsersContainer.style.display === 'none') return;
    openOverlay();
  }
  stackTrigger?.addEventListener('click', openOnClick);
  stackTrigger?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openOnClick(e);
    }
  });
  closeBtn?.addEventListener('click', closeOverlay);
  backdrop?.addEventListener('click', closeOverlay);

  function setSearchIcon(isOpen) {
    var icon = searchIcon || searchBtn?.querySelector('i');
    if (!icon) return;
    icon.classList.remove('fa-search', 'fa-times');
    icon.classList.add(isOpen ? 'fa-times' : 'fa-search');
    if (searchBtn) {
      searchBtn.setAttribute('aria-label', isOpen ? 'Close search' : 'Search');
    }
  }

  function showSearchInput() {
    if (!searchInput) return;
    const count = getLikedCount();
    if (count >= SEARCH_MIN_USERS) searchActiveWithMany = true;
    searchInput.style.display = '';
    searchInput.focus();
    setSearchIcon(true);
    updateModalHeight(count, searchActiveWithMany);
  }

  function hideSearchInput() {
    if (!searchInput) return;
    searchActiveWithMany = false;
    searchInput.style.display = 'none';
    searchInput.value = '';
    filterLikedUsers('');
    setSearchIcon(false);
    updateModalHeight(getLikedCount(), false);
  }

  function filterLikedUsers(query) {
    if (!list) return;
    const q = (query || '').trim().toLowerCase().replace(/\s+/g, ' ');
    const items = Array.from(list.querySelectorAll('.liked-users-item'));
    const partialMatches = [];
    const exactMatches = [];

    items.forEach(function (item) {
      const rawUsername = item.getAttribute('data-like-user') || '';
      const username = rawUsername.toLowerCase().trim().replace(/\s+/g, ' ');
      const badge = item.querySelector('.custom_badge');
      const rawLabel = badge ? badge.textContent : '';
      const label = rawLabel.trim().toLowerCase().replace(/\s+/g, ' ');
      const exact = q && (username === q || label === q);
      const partial = !q || username.indexOf(q) !== -1 || label.indexOf(q) !== -1;

      if (exact) exactMatches.push(item);
      if (partial) partialMatches.push(item);
    });

    var toShow = [];
    if (q) {
      toShow = exactMatches.length > 0 ? exactMatches : partialMatches;
    } else {
      restoreInitialOrder();
      toShow = items;
    }

    items.forEach(function (item) {
      item.style.setProperty('display', 'none', 'important');
    });
    toShow.forEach(function (item) {
      item.style.setProperty('display', 'flex', 'important');
    });

    if (q && toShow.length) {
      for (var i = toShow.length - 1; i >= 0; i--) {
        list.insertBefore(toShow[i], list.firstChild);
      }
    }

    var noMatches = q && toShow.length === 0;
    if (emptyMsg) {
      emptyMsg.style.display = noMatches ? 'flex' : 'none';
    }
    list.style.display = noMatches ? 'none' : 'flex';

    var count = getLikedCount();
    updateModalHeight(count, searchActiveWithMany && count >= SEARCH_MIN_USERS, noMatches);
  }

  searchBtn?.addEventListener('click', function (e) {
    e.stopPropagation();
    if (searchInput && searchInput.style.display !== 'none') {
      hideSearchInput();
    } else {
      showSearchInput();
    }
  });

  searchInput?.addEventListener('input', function () {
    filterLikedUsers(this.value);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeOverlay();
  });
  list?.addEventListener('click', (e) => {
    const link = e.target.closest?.('a');
    if (!link) return;
    closeOverlay();
  });
  window.addEventListener('pagehide', closeOverlay);
  /* bfcache restore only — avoid running on every tab focus (that caused stray unlockScroll / scroll jumps) */
  window.addEventListener('pageshow', function (ev) {
    if (ev.persisted && overlay && !overlay.classList.contains('hidden')) {
      closeOverlay();
    }
  });
  window.addEventListener('resize', () => {
    /* Два rAF после смены viewport (открытие DevTools и т.д.), чтобы measureItemHeight видел финальный layout */
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        updateModalHeight(getLikedCount(), searchActiveWithMany, isEmptyStateActive());
      });
    });
  });

  function upsertListItem(username, avatarUrl, profileUrl) {
    if (!list) return;
    const existing = list.querySelector(`[data-like-user="${username}"]`);
    if (existing) return;
    const row = document.createElement('a');
    row.href = profileUrl || '#';
    row.className = 'liked-users-item d-flex align-items-center gap-2 text-decoration-none';
    row.setAttribute('data-like-user', username);
    const avatarWrap = document.createElement('div');
    avatarWrap.className = 'liked-user-avatar little-avatar';
    const img = document.createElement('img');
    img.src = avatarUrl;
    img.alt = username;
    img.className = 'user-avatar';
    img.width = 30;
    img.height = 30;
    img.decoding = 'async';
    img.loading = 'lazy';
    img.onerror = function () { this.onerror = null; this.classList.add('avatar-load-failed'); };
    avatarWrap.appendChild(img);
    const badge = document.createElement('span');
    badge.className = 'custom_badge badge_primary';
    badge.textContent = username;
    row.appendChild(avatarWrap);
    row.appendChild(badge);
    list.prepend(row);
    initialOrder.unshift(row);
  }

  function removeListItem(username) {
    if (!list) return;
    const existing = list.querySelector(`[data-like-user="${username}"]`);
    if (existing) {
      existing.remove();
      initialOrder = initialOrder.filter(function (item) { return item !== existing; });
    }
  }

  function syncStackFromList() {
    if (!stack || !list) return;
    const items = Array.from(list.querySelectorAll('[data-like-user]')).slice(0, 5);

    function rebuild() {
      stack.classList.remove('is-refreshing-out');
      stack.innerHTML = '';
      items.forEach((row) => {
        const username = row.dataset.likeUser;
        const sourceImg = row.querySelector('img');
        const span = document.createElement('span');
        span.className = 'liked-user-avatar little-avatar';
        span.title = username;
        const img = document.createElement('img');
        if (sourceImg && sourceImg.classList.contains('avatar-load-failed')) {
          img.classList.add('avatar-load-failed');
          img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>';
        } else {
          img.src = (sourceImg && sourceImg.getAttribute('src')) || '/static/img/no_avatar.svg';
        }
        img.alt = username;
        img.className = 'user-avatar';
        img.width = 30;
        img.height = 30;
        img.decoding = 'async';
        img.loading = 'lazy';
        img.onerror = function () { this.onerror = null; this.classList.add('avatar-load-failed'); };
        span.appendChild(img);
        stack.appendChild(span);
      });
    }

    if (stack.querySelector('.liked-user-avatar')) {
      stack.classList.add('is-refreshing-out');
      window.setTimeout(rebuild, 150);
    } else {
      rebuild();
    }
  }

  function updateButtonVisibility(likesCount) {
    const hasLikes = likesCount >= 1;
    if (noLikesYet) {
      noLikesYet.style.display = hasLikes ? 'none' : '';
    }
    if (likedUsersContainer) {
      likedUsersContainer.style.display = hasLikes ? '' : 'none';
    }
    if (!hasLikes && overlay && !overlay.classList.contains('hidden')) {
      closeOverlay();
    }
  }

  window.updateLikedUsersUI = function (data) {
    if (!current || !data) return;
    const username = current.dataset.username;
    const avatar = current.dataset.avatar;
    const profileUrl = current.dataset.profileUrl;
    if (!username) return;

    if (data.liked) {
      upsertListItem(username, avatar, profileUrl);
      syncStackFromList();
    } else {
      removeListItem(username);
      syncStackFromList();
    }
    if (typeof data.likes_count === 'number') {
      updateButtonVisibility(data.likes_count);
    }
    var count = getLikedCount();
    updateSearchWrapVisibility(count);
    if (count <= 50 && searchInput && searchInput.style.display !== 'none') {
      searchActiveWithMany = false;
      searchInput.style.display = 'none';
      searchInput.value = '';
      filterLikedUsers('');
      setSearchIcon(false);
    }
    updateModalHeight(count, searchActiveWithMany);
  };
})();
