// Open fullscreen search overlay from header or mobile bottom nav (event delegation survives Turbo body swaps).
(function () {
    'use strict';

    if (window.__headerSearchToggleInit) return;
    window.__headerSearchToggleInit = true;

    function openSearch(e) {
        if (e) {
            e.stopPropagation();
            e.preventDefault();
        }
        if (typeof window.openSearchOverlay === 'function') {
            window.openSearchOverlay();
        } else {
            document.dispatchEvent(new CustomEvent('openSearchOverlay'));
        }
    }

    document.addEventListener(
        'click',
        function (e) {
            var t = e.target;
            if (!t || !t.closest) return;
            if (t.closest('.header-actions .search-btn')) {
                openSearch(e);
            }
        },
        true
    );
})();
