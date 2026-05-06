/**
 * Topics index: filter featured + all grids by category chip (client-side).
 * Document-level delegation + capture phase so handlers survive Turbo swaps;
 * touch targets may be Text nodes on iOS WebKit — normalize before .closest().
 */
(function () {
  'use strict';

  if (window.__topicsFilterDelegationBound) return;
  window.__topicsFilterDelegationBound = true;

  /** Text nodes have no .closest — common when tapping label text inside buttons on iOS. */
  function eventTargetElement(target) {
    if (!target) return null;
    return target.nodeType === 1 ? target : target.parentElement;
  }

  function closestFromEventTarget(target, selector) {
    var el = eventTargetElement(target);
    return el && el.closest ? el.closest(selector) : null;
  }

  function slugFromChip(btn) {
    if (!btn) return null;
    if (btn.getAttribute('data-filter') === 'all') return 'all';
    return btn.getAttribute('data-category-slug') || null;
  }

  function matchCol(col, slug) {
    var tile = col.querySelector('.topic-tile');
    if (!tile) return false;
    var tslug = tile.getAttribute('data-category-slug');
    if (slug === 'all') return true;
    return tslug === slug;
  }

  function applyFilter(slug) {
    var nav = document.querySelector('[data-topic-chips-filter]');
    if (!nav) return;

    var chips = nav.querySelectorAll('.topic-category-chip');
    var featuredRow = document.querySelector('.topics-featured-row');
    var grid = document.getElementById('topicsAllGrid');
    var featuredSec = document.getElementById('topicsFeaturedSection');
    var allSec = document.getElementById('topicsAllSection');
    var emptyMsg = document.getElementById('topicsFilterEmpty');

    var isAll = slug === 'all';
    var featVisible = 0;
    var allVisible = 0;

    if (featuredRow) {
      featuredRow.querySelectorAll(':scope > div').forEach(function (col) {
        var show = matchCol(col, slug);
        col.classList.toggle('d-none', !show);
        if (show) featVisible += 1;
      });
    }
    if (grid) {
      grid.querySelectorAll('.topics-grid-col').forEach(function (col) {
        var show = matchCol(col, slug);
        col.classList.toggle('d-none', !show);
        if (show) allVisible += 1;
      });
    }

    var total = featVisible + allVisible;

    if (emptyMsg) {
      emptyMsg.classList.toggle('d-none', total > 0);
    }

    if (featuredSec) {
      if (isAll) {
        featuredSec.classList.remove('d-none');
      } else {
        featuredSec.classList.toggle('d-none', featVisible === 0);
      }
    }
    if (allSec) {
      if (isAll) {
        allSec.classList.remove('d-none');
      } else {
        allSec.classList.toggle('d-none', allVisible === 0);
      }
    }

    var fh = document.getElementById('topicsFeaturedHeading');
    var ah = document.getElementById('topicsAllHeading');
    if (fh) {
      fh.classList.toggle('d-none', !isAll && featVisible === 0);
    }
    if (ah) {
      ah.classList.toggle('d-none', !isAll && allVisible === 0);
    }

    chips.forEach(function (btn) {
      var catSlug = btn.getAttribute('data-category-slug');
      var isAllBtn = btn.getAttribute('data-filter') === 'all';
      var selected = isAll ? isAllBtn : catSlug === slug;
      btn.classList.toggle('is-selected', selected);
      btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
    });

    if (typeof window.scrollFilterSegmentSelectedIntoView === 'function') {
      requestAnimationFrame(function () {
        requestAnimationFrame(window.scrollFilterSegmentSelectedIntoView);
      });
    }
  }

  function activateChipFromEventTarget(target) {
    var btn = closestFromEventTarget(target, '.topic-category-chip');
    if (!btn || !btn.closest('[data-topic-chips-filter]')) return false;
    var slug = slugFromChip(btn);
    if (!slug) return false;
    applyFilter(slug);
    return true;
  }

  var suppressNextClick = false;
  var pendingTap = null;

  function onPointerDown(e) {
    if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
    var el = eventTargetElement(e.target);
    if (!el || !el.closest || !el.closest('[data-topic-chips-filter]')) return;
    pendingTap = { x: e.clientX, y: e.clientY, pid: e.pointerId };
  }

  function onPointerCancel(e) {
    if (pendingTap && pendingTap.pid === e.pointerId) pendingTap = null;
  }

  function onPointerUp(e) {
    if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
    if (e.button !== 0) return;
    var el = eventTargetElement(e.target);
    if (!el || !el.closest || !el.closest('[data-topic-chips-filter]')) return;
    var start = pendingTap;
    pendingTap = null;
    if (!start || start.pid !== e.pointerId) return;
    var dx = Math.abs(e.clientX - start.x);
    var dy = Math.abs(e.clientY - start.y);
    if (dx > 14 || dy > 14) return;
    if (!activateChipFromEventTarget(e.target)) return;
    suppressNextClick = true;
    window.setTimeout(function () {
      suppressNextClick = false;
    }, 550);
  }

  function onClick(e) {
    var el = eventTargetElement(e.target);
    if (!el || !el.closest || !el.closest('[data-topic-chips-filter]')) return;
    if (suppressNextClick) {
      suppressNextClick = false;
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    var btn = closestFromEventTarget(e.target, '.topic-category-chip');
    if (!btn) return;
    e.preventDefault();
    var slug = slugFromChip(btn);
    if (!slug) return;
    applyFilter(slug);
  }

  var optsCapture = true;
  document.addEventListener('pointerdown', onPointerDown, { passive: true, capture: optsCapture });
  document.addEventListener('pointercancel', onPointerCancel, { capture: optsCapture });
  document.addEventListener('pointerup', onPointerUp, { capture: optsCapture });
  document.addEventListener('click', onClick, { capture: optsCapture });
})();
