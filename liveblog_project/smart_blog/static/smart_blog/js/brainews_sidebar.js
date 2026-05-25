(function () {
  'use strict';

  var ROOT_SELECTOR = '[data-brainews-listing]';
  var SIDEBAR_POLL_MS = 30000;
  var NO_AVATAR_SRC = '/static/img/no_avatar.svg';
  var DELETED_AVATAR_SRC = '/static/img/user-deleted.webp';

  function fetchJson(url) {
    return fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    }).then(function (resp) {
      if (!resp.ok) {
        return { ok: false, data: null };
      }
      return resp.json().then(function (data) {
        return { ok: true, data: data };
      });
    });
  }

  function escapeHtml(text) {
    return String(text || '').replace(/[<>&"']/g, function (c) {
      return ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function counterVal(entry, humanKey, rawKey) {
    if (entry[humanKey] != null && entry[humanKey] !== '') {
      return String(entry[humanKey]);
    }
    return String(entry[rawKey] != null ? entry[rawKey] : 0);
  }

  function avatarSrc(entry) {
    if (!entry.is_active) {
      return DELETED_AVATAR_SRC;
    }
    if (entry.avatar_url) {
      return entry.avatar_url;
    }
    return NO_AVATAR_SRC;
  }

  function countersHtml(entry) {
    return ''
      + '<div class="brainews-sidebar-item__counters brainews-sidebar-counters" aria-label="Author stats">'
      +   '<span class="brainews-sidebar-counter" data-counter="posts">'
      +     '<i class="fa fa-file-text-o" aria-hidden="true"></i>'
      +     '<span class="brainews-sidebar-counter__val">' + counterVal(entry, 'post_count_human', 'post_count') + '</span>'
      +   '</span>'
      +   '<span class="brainews-sidebar-counter" data-counter="avg_likes">'
      +     '<i class="fa fa-heart-o" aria-hidden="true"></i>'
      +     '<span class="brainews-sidebar-counter__val">' + counterVal(entry, 'avg_likes_human', 'avg_likes') + '</span>'
      +   '</span>'
      +   '<span class="brainews-sidebar-counter" data-counter="avg_views">'
      +     '<i class="fa fa-eye" aria-hidden="true"></i>'
      +     '<span class="brainews-sidebar-counter__val">' + counterVal(entry, 'avg_views_human', 'avg_views') + '</span>'
      +   '</span>'
      +   '<span class="brainews-sidebar-counter" data-counter="avg_comments">'
      +     '<i class="fa fa-comment" aria-hidden="true"></i>'
      +     '<span class="brainews-sidebar-counter__val">' + counterVal(entry, 'avg_comments_human', 'avg_comments') + '</span>'
      +   '</span>'
      + '</div>';
  }

  function authorItemHtml(entry) {
    var usernameDisplay = escapeHtml(entry.username_display || entry.username || '');
    var usernameTitle = escapeHtml(entry.username_title || entry.username || '');
    var profileUrl = escapeHtml(entry.profile_url || '#');
    var avatarAlt = escapeHtml(entry.username_title || entry.username || 'Author');
    var avatarClass = entry.is_active ? 'user-avatar clickable-avatar' : 'user-avatar';
    var dataUsername = entry.is_active
      ? ' data-username="' + escapeHtml(entry.username) + '"'
      : '';
    var onError = entry.is_active
      ? ' onerror="this.onerror=null;this.classList.add(\'avatar-load-failed\');"'
      : '';

    return ''
      + '<li class="brainews-sidebar-item" data-brainews-sidebar-author="' + entry.id + '">'
      +   '<a href="' + profileUrl + '" class="brainews-sidebar-author-link text-decoration-none" title="' + usernameTitle + '">'
      +     '<div class="brainews-sidebar-author-row">'
      +       '<div class="little-avatar">'
      +         '<img src="' + escapeHtml(avatarSrc(entry)) + '" alt="' + avatarAlt + '" class="' + avatarClass + '" width="35" height="35" loading="lazy" decoding="async"' + dataUsername + onError + ' />'
      +       '</div>'
      +       '<span class="brainews-sidebar-author-name fw-semibold">' + usernameDisplay + '</span>'
      +     '</div>'
      +   '</a>'
      +   countersHtml(entry)
      + '</li>';
  }

  function renderAuthorsList(entries) {
    var ul = document.querySelector('[data-brainews-sidebar-list="authors"]');
    if (!ul) {
      return;
    }
    if (!entries.length) {
      ul.innerHTML = '<li class="text-muted small">No authors yet.</li>';
      return;
    }
    ul.innerHTML = entries.map(authorItemHtml).join('');
  }

  function pollSidebar(root) {
    var resolved = root || document.querySelector(ROOT_SELECTOR);
    if (!resolved) {
      return;
    }
    var url = resolved.getAttribute('data-brainews-sidebar-url');
    if (!url) {
      return;
    }
    fetchJson(url).then(function (resp) {
      if (!resp.ok || !resp.data || !resp.data.ok) {
        return;
      }
      renderAuthorsList(resp.data.authors || []);
    }).catch(function () { /* ignore */ });
  }

  function init() {
    var root = document.querySelector(ROOT_SELECTOR);
    if (!root || !root.getAttribute('data-brainews-sidebar-url')) {
      return;
    }
    pollSidebar(root);
    setInterval(function () {
      pollSidebar(root);
    }, SIDEBAR_POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
