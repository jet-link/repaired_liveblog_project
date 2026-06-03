(function () {
    'use strict';

    if (!document.body.classList.contains('page-item-detail')) return;

    var scope = document.querySelector('.item-detail-sticky-scope');
    if (!scope) return;

    var sentinel = scope.querySelector('.item-detail-sticky-sentinel');
    var panel = scope.querySelector('.item-detail-sticky-panel');
    var spacer = scope.querySelector('.item-detail-sticky-spacer');
    if (!sentinel || !panel || !spacer) return;

    var pinned = false;
    var observer = null;
    var resizeObs = null;

    function getStickyTop() {
        return 0;
    }

    function syncPinnedGeometry() {
        var container = scope.closest('.container-main') || scope.parentElement;
        if (!container) return;
        var rect = container.getBoundingClientRect();
        scope.style.setProperty('--item-detail-sticky-left', rect.left + 'px');
        scope.style.setProperty('--item-detail-sticky-width', rect.width + 'px');
        scope.style.setProperty('--item-detail-sticky-top', getStickyTop() + 'px');
    }

    function syncSpacerHeight() {
        if (!pinned) {
            spacer.style.height = '0';
            return;
        }
        spacer.style.height = panel.offsetHeight + 'px';
    }

    function setPinned(next) {
        if (pinned === next) return;
        pinned = next;
        scope.classList.toggle('is-pinned', pinned);
        panel.classList.toggle('is-pinned', pinned);
        syncSpacerHeight();
    }

    function onIntersect(entries) {
        var entry = entries[0];
        if (!entry) return;
        var top = getStickyTop();
        var shouldPin = !entry.isIntersecting && entry.boundingClientRect.top < top;
        setPinned(shouldPin);
    }

    function mountObserver() {
        if (observer) observer.disconnect();
        syncPinnedGeometry();
        var top = getStickyTop();
        observer = new IntersectionObserver(onIntersect, {
            threshold: [0],
            root: null,
            rootMargin: (-top) + 'px 0px 0px 0px'
        });
        observer.observe(sentinel);
    }

    function init() {
        syncPinnedGeometry();
        mountObserver();

        if (typeof ResizeObserver !== 'undefined') {
            resizeObs = new ResizeObserver(function () {
                syncPinnedGeometry();
                syncSpacerHeight();
            });
            resizeObs.observe(panel);
            var container = scope.closest('.container-main');
            if (container) resizeObs.observe(container);
        }

        window.addEventListener('resize', function () {
            syncPinnedGeometry();
            mountObserver();
            syncSpacerHeight();
        }, { passive: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
