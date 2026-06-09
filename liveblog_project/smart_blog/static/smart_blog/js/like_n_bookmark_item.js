// static/js/like.js
(function () {
  'use strict';

  function humanCount(n) {
    n = Number(n);
    if (isNaN(n) || n < 0) return '0';
    n = Math.floor(n);
    if (n < 1000) return String(n);
    const _u = [[1e9, 'B'], [1e6, 'M'], [1e3, 'K']];
    for (let _i = 0; _i < _u.length; _i++) {
      if (n >= _u[_i][0]) {
        const r = n / _u[_i][0];
        if (r >= 10) return String(Math.floor(r)) + _u[_i][1];
        return (Math.floor(r * 10) / 10).toFixed(1).replace(/\.0$/, '') + _u[_i][1];
      }
    }
    return String(n);
  }

  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))
      ?.split('=')[1];
  }

  function setLikeBtnState(btn, liked) {
    if (!btn) return;
    var icon = btn.querySelector('i');
    var on = !!liked;
    btn.classList.toggle('is-liked', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (icon) {
      icon.classList.toggle('fa-heart', on);
      icon.classList.toggle('fa-heart-o', !on);
    }
  }
  window.setLikeBtnState = setLikeBtnState;

  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('.like-btn');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const url = btn.dataset.url;
    const itemId = btn.dataset.itemId;
    const icon = btn.querySelector('i');

    if (!url || !icon) return;

    const wasLiked = btn.classList.contains('is-liked');
    setLikeBtnState(btn, !wasLiked);
    icon.classList.remove('btn-bounce');
    icon.offsetWidth;
    icon.classList.add('btn-bounce');
    const endBounce = function () {
      icon.classList.remove('btn-bounce');
      icon.removeEventListener('animationend', endBounce);
    };
    icon.addEventListener('animationend', endBounce);

    btn.disabled = true;

    try {
      const resp = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin', // ВОТ
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        }
      });

      const data = await resp.json().catch(() => null);
      if (!resp.ok || !data) {
        setLikeBtnState(btn, wasLiked);
        console.error('LIKE ERROR', resp.status);
        return;
      }

      setLikeBtnState(btn, !!data.liked);
      document.querySelectorAll('.like-btn[data-item-id="' + itemId + '"]').forEach(function (otherBtn) {
        if (otherBtn !== btn) setLikeBtnState(otherBtn, !!data.liked);
      });

      // if we came from profile listing, ensure it refreshes on return
      try {
        const listingUrl = sessionStorage.getItem('listing_url') || '';
        if (data.liked === true && listingUrl.includes('/profile/')) {
          sessionStorage.setItem('profile_refresh_needed', '1');
          sessionStorage.setItem('profile_refresh_section', 'liked');
        }
      } catch { }

      // sync listing
      try {
        const key = 'listing_changes';
        const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
        changes[itemId] = changes[itemId] || {};
        changes[itemId].likes_count = data.likes_count;
        changes[itemId].liked = data.liked;
        changes[itemId].user_id = document.body.dataset.userId || '';
        if (typeof data.views_count === 'number') changes[itemId].views_count = data.views_count;
        sessionStorage.setItem(key, JSON.stringify(changes));
        try { localStorage.setItem('brainews_filter_refresh_needed', '1'); } catch (e) { }
        try { document.dispatchEvent(new CustomEvent('brainews-filter-refresh')); } catch (e) { }
      } catch { }

      const detailLikes = document.getElementById('likesCount');
      if (detailLikes && data.likes_count != null) {
        detailLikes.textContent = humanCount(data.likes_count);
      }
      const cardLikes = document.getElementById('likes-count-' + itemId);
      if (cardLikes && data.likes_count != null) {
        cardLikes.textContent = humanCount(data.likes_count);
      }
      if (window.updateLikedUsersUI) {
        window.updateLikedUsersUI(data);
      }
    } catch (err) {
      setLikeBtnState(btn, wasLiked);
    } finally {
      btn.disabled = false;
    }
  });

})();



// static/js/bookmark.js
(function () {
  'use strict';

  function humanCount(n) {
    n = Number(n);
    if (isNaN(n) || n < 0) return '0';
    n = Math.floor(n);
    if (n < 1000) return String(n);
    const _u = [[1e9, 'B'], [1e6, 'M'], [1e3, 'K']];
    for (let _i = 0; _i < _u.length; _i++) {
      if (n >= _u[_i][0]) {
        const r = n / _u[_i][0];
        if (r >= 10) return String(Math.floor(r)) + _u[_i][1];
        return (Math.floor(r * 10) / 10).toFixed(1).replace(/\.0$/, '') + _u[_i][1];
      }
    }
    return String(n);
  }

  function getCookie(name) {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))
      ?.split('=')[1];
  }

  function setBookmarkBtnState(btn, bookmarked) {
    if (!btn) return;
    var icon = btn.querySelector('i');
    var on = !!bookmarked;
    btn.classList.toggle('is-bookmarked', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (icon) {
      icon.classList.toggle('fa-bookmark', on);
      icon.classList.toggle('fa-bookmark-o', !on);
    }
  }

  function setReadingBadgeForItem(itemId, visible) {
    if (itemId) {
      const cardBadge = document.getElementById('reading-badge-' + itemId);
      if (cardBadge) cardBadge.hidden = !visible;
    }
    /* item_detail "I'll read it" badge disabled — see item_detail.html
    const bodyId = document.body.dataset.itemId;
    if (bodyId != null && String(bodyId) === String(itemId)) {
      const detailBadge = document.getElementById('itemReadingBadge');
      if (detailBadge) detailBadge.hidden = !visible;
    }
    */
  }

  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('.bookmark-btn');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const url = btn.dataset.url;
    const itemId = btn.dataset.itemId;
    const icon = btn.querySelector('i');

    if (!url || !icon) return;

    const wasBookmarked = btn.classList.contains('is-bookmarked');
    setReadingBadgeForItem(itemId, !wasBookmarked);
    setBookmarkBtnState(btn, !wasBookmarked);
    icon.classList.remove('btn-bounce');
    icon.offsetWidth;
    icon.classList.add('btn-bounce');
    const endBm = function () {
      icon.classList.remove('btn-bounce');
      icon.removeEventListener('animationend', endBm);
    };
    icon.addEventListener('animationend', endBm);

    btn.disabled = true;

    try {
      const resp = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin', // ВОТ
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        }
      });

      const data = await resp.json().catch(() => null);
      if (!resp.ok || !data) {
        setReadingBadgeForItem(itemId, wasBookmarked);
        setBookmarkBtnState(btn, wasBookmarked);
        console.error('BOOKMARK ERROR', resp.status);
        return;
      }

      setBookmarkBtnState(btn, !!data.bookmarked);
      setReadingBadgeForItem(itemId, !!data.bookmarked);

      // if we came from profile listing, ensure it refreshes on return
      try {
        const listingUrl = sessionStorage.getItem('listing_url') || '';
        if (data.bookmarked === true && listingUrl.includes('/profile/')) {
          sessionStorage.setItem('profile_refresh_needed', '1');
          sessionStorage.setItem('profile_refresh_section', 'bookmarked');
        }
      } catch { }

      // sync listing
      try {
        const key = 'listing_changes';
        const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
        changes[itemId] = changes[itemId] || {};
        changes[itemId].bookmarks_count = data.bookmarks_count;
        changes[itemId].bookmarked = data.bookmarked;
        changes[itemId].user_id = document.body.dataset.userId || '';
        if (typeof data.views_count === 'number') changes[itemId].views_count = data.views_count;
        sessionStorage.setItem(key, JSON.stringify(changes));
        try { localStorage.setItem('brainews_filter_refresh_needed', '1'); } catch (e) { }
        try { document.dispatchEvent(new CustomEvent('brainews-filter-refresh')); } catch (e) { }
      } catch { }

      const detailBookmarks = document.getElementById('bookmarksCount');
      if (detailBookmarks && data.bookmarks_count != null) {
        detailBookmarks.textContent = humanCount(data.bookmarks_count);
      }
      const cardBookmarks = document.getElementById('bookmarks-count-' + itemId);
      if (cardBookmarks && data.bookmarks_count != null) {
        cardBookmarks.textContent = humanCount(data.bookmarks_count);
      }
    } catch (err) {
      setReadingBadgeForItem(itemId, wasBookmarked);
      setBookmarkBtnState(btn, wasBookmarked);
    } finally {
      btn.disabled = false;
    }
  });
})();