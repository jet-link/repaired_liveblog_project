/**
 * Sign out confirmation modal -- opens on .signout-trigger click,
 * confirms via POST form submit, cancels with Cancel or backdrop.
 */
(function() {
  'use strict';

  if (window.__signoutModalInit) return;
  window.__signoutModalInit = true;

  document.addEventListener('click', function(e) {
    var trigger = e.target && e.target.closest ? e.target.closest('.signout-trigger') : null;
    if (!trigger) return;
    e.preventDefault();

    var closeMenuBtn = document.getElementById('bottomMenuClose');
    var sideMenu = document.getElementById('bottomSideMenu');
    if (closeMenuBtn && sideMenu && sideMenu.classList.contains('open')) {
      closeMenuBtn.click();
    }
    if (typeof window.__closeMobileNavPopovers === 'function') {
      window.__closeMobileNavPopovers();
    } else if (typeof window.__closeMobileAccountPopover === 'function') {
      window.__closeMobileAccountPopover();
    }

    var modalEl = document.getElementById('signoutConfirmModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
      requestAnimationFrame(function() {
        setTimeout(function() {
          bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }, 50);
      });
    }
  }, true);
})();
