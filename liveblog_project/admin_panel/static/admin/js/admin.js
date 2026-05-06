/**
 * Admin panel JS - theme toggle, mobile sidebar, instant search, confirm
 */
(function() {
  'use strict';

  /* Turbo re-evaluates body scripts on visits — without this, every listener is registered again.
     Double theme/collapse handlers each fire once per click = toggle twice = no visible effect. */
  if (window.__adminPanelCoreInit) return;
  window.__adminPanelCoreInit = true;

  var STORAGE_THEME = 'admin_theme';

  function isAdminAppPath(pathname) {
    if (!pathname) return false;
    return pathname === '/admin' || pathname.indexOf('/admin/') === 0;
  }

  function syncAdminSidebarActiveFromNewBody(newBody) {
    if (!newBody) return;
    var newSb = newBody.querySelector('#adminSidebar');
    var oldSb = document.getElementById('adminSidebar');
    if (!newSb || !oldSb) return;
    var newLinks = newSb.querySelectorAll('a.admin-nav-item[href]');
    newLinks.forEach(function(newLink) {
      var href = newLink.getAttribute('href');
      if (!href) return;
      var oldLink = null;
      var oldLinks = oldSb.querySelectorAll('a.admin-nav-item[href]');
      for (var i = 0; i < oldLinks.length; i++) {
        if (oldLinks[i].getAttribute('href') === href) {
          oldLink = oldLinks[i];
          break;
        }
      }
      if (!oldLink) return;
      if (newLink.classList.contains('active')) oldLink.classList.add('active');
      else oldLink.classList.remove('active');
    });
  }

  (function initAdminTurbo() {
    if (typeof Turbo === 'undefined' || !Turbo.session) return;
    var mq = window.matchMedia('(min-width: 993px)');
    function syncDrive() {
      Turbo.session.drive = mq.matches;
    }
    syncDrive();
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', syncDrive);
    } else {
      mq.addListener(syncDrive);
    }
    document.documentElement.addEventListener('turbo:before-visit', function(event) {
      if (!mq.matches) return;
      var raw = event.detail.url;
      if (raw == null || raw === '') return;
      /* Turbo 8 may pass a string; url.pathname / url.href would be wrong and yield /admin/undefined */
      var u = raw instanceof URL ? raw : new URL(String(raw), window.location.origin);
      if (!isAdminAppPath(u.pathname)) {
        event.preventDefault();
        window.location.href = u.href;
      }
    });
    document.documentElement.addEventListener('turbo:before-render', function(event) {
      if (!mq.matches) return;
      var detail = event.detail;
      var newBody = detail && detail.newBody;
      if (newBody) syncAdminSidebarActiveFromNewBody(newBody);
    });
  })();

  // Theme: light → moon (click to dark), dark → sun (click to light)
  function getAdminTheme() {
    return document.documentElement.getAttribute('data-theme') || '';
  }
  function isAdminLight() {
    return getAdminTheme() === 'light';
  }
  function syncAdminThemeIcon() {
    var icon = document.querySelector('#adminThemeToggle .admin-theme-icon');
    if (!icon) return;
    var light = isAdminLight();
    icon.classList.remove('fa-moon', 'fa-sun');
    icon.classList.add(light ? 'fa-moon' : 'fa-sun');
  }
  function setAdminTheme(light) {
    var root = document.documentElement;
    if (light) {
      root.setAttribute('data-theme', 'light');
      try { localStorage.setItem(STORAGE_THEME, 'light'); } catch (e) {}
    } else {
      root.removeAttribute('data-theme');
      try { localStorage.setItem(STORAGE_THEME, 'dark'); } catch (e) {}
    }
    syncAdminThemeIcon();
  }

  (function initAdminTheme() {
    var root = document.documentElement;
    var saved = localStorage.getItem(STORAGE_THEME);
    if (saved === 'light') root.setAttribute('data-theme', 'light');
    syncAdminThemeIcon();

    document.addEventListener('click', function(e) {
      if (!e.target.closest('#adminThemeToggle')) return;
      e.preventDefault();
      setAdminTheme(!isAdminLight());
    }, true);

    var observer = new MutationObserver(function(mutations) {
      for (var i = 0; i < mutations.length; i++) {
        if (mutations[i].attributeName === 'data-theme') {
          syncAdminThemeIcon();
          break;
        }
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  })();

  // Mobile sidebar
  var mobileNavScrollY = 0;

  function getAdminSidebar() {
    return document.getElementById('adminSidebar');
  }

  function getSidebarCollapseIconEl() {
    var btn = document.getElementById('adminSidebarCollapseToggle');
    return btn && btn.querySelector('.admin-sidebar-toggle-icon');
  }

  function closeAdminHeaderOverflowMenu() {
    var wrap = document.getElementById('adminHeaderOverflowMenu');
    if (!wrap) return;
    wrap.classList.remove('open');
    var btn = wrap.querySelector('.comment-menu-btn');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function openSidebar() {
    closeAllAdminDropdowns();
    closeAdminHeaderOverflowMenu();
    if (window.innerWidth > 1019) return;
    var sb = document.getElementById('adminSidebar');
    var ov = document.getElementById('adminSidebarOverlay');
    var mt = document.getElementById('adminMenuToggle');
    var main = document.querySelector('.admin-main');
    var layout = document.querySelector('.admin-layout');
    if (sb) sb.classList.add('is-open');
    if (ov) { ov.classList.add('is-open'); ov.setAttribute('aria-hidden', 'false'); }
    if (mt) mt.setAttribute('aria-expanded', 'true');
    document.documentElement.classList.add('admin-mobile-nav-open');
    document.body.classList.add('admin-mobile-nav-open');
    mobileNavScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + mobileNavScrollY + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
    if (layout) layout.style.overflow = 'hidden';
    if (main) main.style.overflow = 'hidden';
  }
  function closeSidebar() {
    var hadMobileLock = document.body.classList.contains('admin-mobile-nav-open');
    var sb = document.getElementById('adminSidebar');
    var ov = document.getElementById('adminSidebarOverlay');
    var mt = document.getElementById('adminMenuToggle');
    var main = document.querySelector('.admin-main');
    var layout = document.querySelector('.admin-layout');
    if (sb) sb.classList.remove('is-open');
    if (ov) { ov.classList.remove('is-open'); ov.setAttribute('aria-hidden', 'true'); }
    if (mt) mt.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('admin-mobile-nav-open');
    document.body.classList.remove('admin-mobile-nav-open');
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    if (layout) layout.style.overflow = '';
    if (main) main.style.overflow = '';
    if (hadMobileLock) {
      window.scrollTo(0, mobileNavScrollY);
    }
  }

  document.addEventListener('click', function(e) {
    if (e.target.closest('#adminMenuToggle')) {
      openSidebar();
      return;
    }
    if (e.target.closest('#adminSidebarClose')) {
      closeSidebar();
      return;
    }
    if (e.target.closest('#adminSidebarOverlay')) {
      closeSidebar();
    }
  });

  // Sidebar collapse toggle (desktop) — delegate so it keeps working after Turbo / DOM swaps
  var STORAGE_COLLAPSED = 'admin_sidebar_collapsed';

  function applyCollapsed(collapsed) {
    var sb = getAdminSidebar();
    if (!sb) return;
    var icon = getSidebarCollapseIconEl();
    var root = document.documentElement;
    if (collapsed) {
      root.classList.add('admin-sidebar-collapsed');
      sb.classList.add('admin-sidebar-collapsed');
      if (icon) { icon.classList.remove('fa-angle-left'); icon.classList.add('fa-angle-right'); }
    } else {
      root.classList.remove('admin-sidebar-collapsed');
      sb.classList.remove('admin-sidebar-collapsed');
      if (icon) { icon.classList.remove('fa-angle-right'); icon.classList.add('fa-angle-left'); }
    }
    try { localStorage.setItem(STORAGE_COLLAPSED, collapsed ? '1' : ''); } catch (e) {}
  }

  (function initCollapse() {
    if (window.innerWidth >= 993) {
      var saved = localStorage.getItem(STORAGE_COLLAPSED);
      var sb = getAdminSidebar();
      if (saved === '1') {
        applyCollapsed(true);
      } else if (document.documentElement.classList.contains('admin-sidebar-collapsed') && sb) {
        sb.classList.add('admin-sidebar-collapsed');
        var icon = getSidebarCollapseIconEl();
        if (icon) { icon.classList.remove('fa-angle-left'); icon.classList.add('fa-angle-right'); }
      }
    }
  })();

  document.addEventListener('click', function(e) {
    if (!e.target.closest('#adminSidebarCollapseToggle')) return;
    e.preventDefault();
    if (window.innerWidth < 993) return;
    var sb = getAdminSidebar();
    if (!sb) return;
    var collapsed = sb.classList.contains('admin-sidebar-collapsed');
    applyCollapsed(!collapsed);
  }, true);

  window.addEventListener('resize', function() {
    closeAllAdminDropdowns();
    if (window.innerWidth > 1019) {
      var sb = getAdminSidebar();
      if (sb && sb.classList.contains('is-open')) {
        closeSidebar();
      }
    }
    if (window.innerWidth < 993) {
      document.documentElement.classList.remove('admin-sidebar-collapsed');
      var sbNarrow = getAdminSidebar();
      if (sbNarrow) sbNarrow.classList.remove('admin-sidebar-collapsed');
      var iconNarrow = getSidebarCollapseIconEl();
      if (iconNarrow) { iconNarrow.classList.remove('fa-angle-right'); iconNarrow.classList.add('fa-angle-left'); }
    } else {
      var saved = localStorage.getItem(STORAGE_COLLAPSED);
      if (saved === '1') applyCollapsed(true);
    }
  });

  // Close sidebar on nav click (mobile) or escape (dropdowns first)
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      var signoutEl = document.getElementById('adminSignoutModal');
      if (signoutEl && signoutEl.classList.contains('is-open')) {
        return;
      }
      if (document.querySelector('.admin-header-overflow-menu.open')) {
        closeAdminHeaderOverflowMenu();
        return;
      }
      if (document.querySelector('.admin-dropdown.is-open')) closeAllAdminDropdowns();
      else closeSidebar();
    }
  });
  document.addEventListener('click', function(e) {
    var navLink = e.target.closest('a.admin-nav-item');
    if (!navLink || !navLink.closest('#adminSidebar')) return;
    if (window.innerWidth <= 992) closeSidebar();
  });

  // Debounce helper (300ms for instant search)
  function debounce(fn, ms) {
    var timeout;
    return function() {
      var ctx = this, args = arguments;
      clearTimeout(timeout);
      timeout = setTimeout(function() { fn.apply(ctx, args); }, ms);
    };
  }

  function bindInstantSearch(scope) {
    var root = scope || document;
    root.querySelectorAll('[data-instant-search]:not([data-admin-instant-search-bound])').forEach(function(input) {
      input.setAttribute('data-admin-instant-search-bound', '1');
      var form = input.closest('form');
      if (form) {
        input.addEventListener('input', debounce(function() { form.submit(); }, 300));
      }
    });
  }

  bindInstantSearch(document);

  // Dropdowns: portal menu to body so overflow on .admin-table-wrapper / .admin-card never clips it
  var adminDdSeq = 0;

  function ensureAdminDdId(dd) {
    if (!dd.id) dd.id = 'admin-dd-' + (++adminDdSeq);
    return dd.id;
  }

  function findAdminDropdownMenu(dd) {
    if (!dd) return null;
    var m = dd.querySelector(':scope > .admin-dropdown-menu');
    if (m) return m;
    var id = dd.id;
    if (!id) return null;
    return document.querySelector('.admin-dropdown-menu[data-admin-dropdown-portal-of="' + id + '"]');
  }

  var adminFormAnchorRow = typeof WeakMap !== 'undefined' ? new WeakMap() : null;

  function attachMenuFormRows(menu, tr) {
    if (!adminFormAnchorRow || !tr) return;
    menu.querySelectorAll('form').forEach(function(f) {
      adminFormAnchorRow.set(f, tr);
    });
  }

  function detachMenuFormRows(menu) {
    if (!adminFormAnchorRow) return;
    menu.querySelectorAll('form').forEach(function(f) {
      adminFormAnchorRow.delete(f);
    });
  }

  window.adminFormAnchorRow = function(form) {
    return adminFormAnchorRow ? adminFormAnchorRow.get(form) : undefined;
  };

  function restoreAdminDropdownMenu(dd, menu) {
    if (!dd || !menu) return;
    detachMenuFormRows(menu);
    menu.removeAttribute('data-admin-dropdown-portal-of');
    menu.classList.remove('is-open');
    menu.style.left = '';
    menu.style.top = '';
    if (menu.parentNode !== dd) dd.appendChild(menu);
  }

  function closeAdminDropdown(dd) {
    if (!dd) return;
    var menu = findAdminDropdownMenu(dd);
    dd.classList.remove('is-open');
    if (menu) {
      menu.classList.remove('is-open');
      if (menu.parentNode === document.body) restoreAdminDropdownMenu(dd, menu);
    }
  }

  function closeAllAdminDropdowns() {
    document.querySelectorAll('.admin-dropdown.is-open').forEach(closeAdminDropdown);
  }

  window.adminFindDropdownMenu = findAdminDropdownMenu;
  window.adminCloseDropdown = closeAdminDropdown;

  function bindAdminDropdowns(scope) {
    var root = scope || document;
    root.querySelectorAll('.admin-dropdown:not([data-admin-dd-inited])').forEach(function(dd) {
      dd.setAttribute('data-admin-dd-inited', '1');
      var trigger = dd.querySelector('.admin-dropdown-trigger');
      var menu = dd.querySelector('.admin-dropdown-menu');
      if (!trigger || !menu) return;
      menu.addEventListener('click', function(e) {
        e.stopPropagation();
      });
      trigger.addEventListener('click', function(e) {
        e.stopPropagation();
        var wasOpen = dd.classList.contains('is-open');
        closeAllAdminDropdowns();
        if (wasOpen) return;
        dd.classList.add('is-open');
        menu.classList.add('is-open');
        menu.setAttribute('data-admin-dropdown-portal-of', ensureAdminDdId(dd));
        document.body.appendChild(menu);
        attachMenuFormRows(menu, dd.closest('tr'));
        function positionMenu() {
          var tr = trigger.getBoundingClientRect();
          var mw = menu.offsetWidth || 140;
          var mh = menu.offsetHeight || 200;
          var gap = 4;
          var pad = 8;
          var winW = window.innerWidth;
          var winH = window.innerHeight;
          var left = tr.right - mw;
          if (left < pad) left = pad;
          if (left + mw > winW - pad) left = Math.max(pad, winW - mw - pad);
          var top = tr.bottom + gap;
          if (top + mh > winH - pad) {
            top = tr.top - mh - gap;
            if (top < pad) top = pad;
          }
          menu.style.left = Math.round(left) + 'px';
          menu.style.top = Math.round(top) + 'px';
        }
        positionMenu();
        requestAnimationFrame(positionMenu);
      });
    });
  }

  bindAdminDropdowns(document);

  document.addEventListener('click', function() {
    closeAllAdminDropdowns();
    closeAdminHeaderOverflowMenu();
  });

  document.addEventListener('click', function(e) {
    var menuBtn = e.target.closest('#adminHeaderOverflowMenu .comment-menu-btn');
    if (!menuBtn) return;
    e.preventDefault();
    e.stopPropagation();
    var wrap = document.getElementById('adminHeaderOverflowMenu');
    if (!wrap) return;
    var wasOpen = wrap.classList.contains('open');
    closeAllAdminDropdowns();
    closeAdminHeaderOverflowMenu();
    if (!wasOpen) {
      wrap.classList.add('open');
      menuBtn.setAttribute('aria-expanded', 'true');
    }
  }, true);

  window.addEventListener('scroll', function() {
    closeAllAdminDropdowns();
    closeAdminHeaderOverflowMenu();
  }, true);

  /* Drop stale wiring before Turbo snapshots the page (so cached HTML doesn't carry
     a "data-admin-dd-inited" flag with no live listeners) and before BFCache restore. */
  function resetAdminDropdownsForCache() {
    document.querySelectorAll('.admin-dropdown.is-open').forEach(closeAdminDropdown);
    /* Any portaled menus still in <body> get pulled back into their owners. */
    document.querySelectorAll('.admin-dropdown-menu[data-admin-dropdown-portal-of]').forEach(function(menu) {
      var ownerId = menu.getAttribute('data-admin-dropdown-portal-of');
      var owner = ownerId ? document.getElementById(ownerId) : null;
      if (owner) restoreAdminDropdownMenu(owner, menu);
    });
    document.querySelectorAll('.admin-dropdown[data-admin-dd-inited]').forEach(function(dd) {
      dd.removeAttribute('data-admin-dd-inited');
      dd.classList.remove('is-open');
    });
    /* Reset bulk-table init flag so listeners are reattached on next bind. */
    document.querySelectorAll('.admin-table[data-admin-bulk-inited]').forEach(function(t) {
      t.removeAttribute('data-admin-bulk-inited');
    });
  }

  document.documentElement.addEventListener('turbo:before-cache', resetAdminDropdownsForCache);

  /* Native back/forward (BFCache) restore — re-init when JS state isn't fresh. */
  window.addEventListener('pageshow', function(e) {
    if (e.persisted) {
      resetAdminDropdownsForCache();
      bindAdminDropdowns(document);
      if (typeof window.adminBulkReinitTables === 'function') {
        window.adminBulkReinitTables();
      }
    }
  });

  document.documentElement.addEventListener('turbo:load', function() {
    syncAdminThemeIcon();
    bindInstantSearch(document);
    bindAdminDropdowns(document);
    if (typeof window.adminBindToolbarSelectFilters === 'function') {
      window.adminBindToolbarSelectFilters(document);
    }
    if (typeof window.adminBulkReinitTables === 'function') {
      window.adminBulkReinitTables();
    }
  });

  // Sign out confirmation modal
  var signoutModalTrigger = null;

  function openSignoutModal(trigger) {
    var signoutModal = document.getElementById('adminSignoutModal');
    if (!signoutModal) return;
    signoutModalTrigger = trigger || null;
    signoutModal.removeAttribute('hidden');
    signoutModal.classList.add('is-open');
    signoutModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeSignoutModal() {
    var signoutModal = document.getElementById('adminSignoutModal');
    if (!signoutModal) return;
    if (signoutModal.contains(document.activeElement)) {
      if (signoutModalTrigger && typeof signoutModalTrigger.focus === 'function') {
        signoutModalTrigger.focus({ preventScroll: true });
      } else {
        var fallback = document.querySelector('.admin-signout-trigger, .admin-header button');
        if (fallback) fallback.focus({ preventScroll: true });
      }
    }
    signoutModal.classList.remove('is-open');
    signoutModal.setAttribute('aria-hidden', 'true');
    signoutModal.setAttribute('hidden', '');
    document.body.style.overflow = '';
    signoutModalTrigger = null;
  }

  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.admin-signout-trigger');
    if (!btn) return;
    e.preventDefault();
    closeAdminHeaderOverflowMenu();
    openSignoutModal(btn);
  }, true);

  document.addEventListener('click', function(e) {
    if (e.target.closest('#adminSignoutModalBackdrop')) closeSignoutModal();
  });
  document.addEventListener('click', function(e) {
    if (e.target.closest('#adminSignoutCancelBtn')) closeSignoutModal();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Escape') return;
    var signoutModal = document.getElementById('adminSignoutModal');
    if (signoutModal && signoutModal.classList.contains('is-open')) {
      closeSignoutModal();
    }
  });

})();
