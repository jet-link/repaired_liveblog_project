/**
 * Horizontal segment strips (.filter-segment-scroll): scroll the selected chip
 * (.filter-reason-btn.is-selected) into a comfortable view — centered when possible,
 * with minimum padding from the scrollport edges.
 */
(function () {
    'use strict';

    /** Minimum space (px) between selected chip and inner edge of scrollport when scrolling. */
    var COMFORT_PAD = 28;

    /** Mobile: stretch chip row to full width only when it fits without horizontal scroll (see styles.css). */
    var EVEN_MOBILE_MQ = '(max-width: 575px)';
    var EVEN_MOBILE_CLASS = 'filter-segment-scroll--even-mobile';
    var _evenMobileResizeTimer;

    function updateFilterSegmentEvenMobile() {
        var mq = window.matchMedia && window.matchMedia(EVEN_MOBILE_MQ);
        var mobile = !!(mq && mq.matches);
        document.querySelectorAll('.filter-segment-scroll.filter-scroll-x').forEach(function (el) {
            if (!mobile) {
                el.classList.remove(EVEN_MOBILE_CLASS);
                return;
            }
            var fits = el.scrollWidth <= el.clientWidth + 2;
            el.classList.toggle(EVEN_MOBILE_CLASS, fits);
        });
    }

    window.updateFilterSegmentEvenMobile = updateFilterSegmentEvenMobile;

    /**
     * @param {Element} scrollEl
     * @param {{ behavior?: 'smooth' | 'auto' }} [opts]  Use 'auto' after AJAX/HTML swap: new scrollports
     *   start at scrollLeft 0; smooth scroll fights native focus/scrollIntoView on mobile Safari.
     */
    function scrollOneSegment(scrollEl, opts) {
        var selected = scrollEl.querySelector('.filter-reason-btn.is-selected');
        if (!selected) return;
        if (scrollEl.scrollWidth <= scrollEl.clientWidth + 1) return;

        var behavior = (opts && opts.behavior) || 'smooth';

        var sr = scrollEl.getBoundingClientRect();
        var br = selected.getBoundingClientRect();
        var sl = scrollEl.scrollLeft;
        var chipLeft = sl + (br.left - sr.left);
        var chipRight = chipLeft + br.width;
        var vw = scrollEl.clientWidth;
        var maxScroll = Math.max(0, scrollEl.scrollWidth - vw);

        var center = chipLeft + br.width / 2 - vw / 2;
        var lo = Math.max(0, chipRight - vw + COMFORT_PAD);
        var hi = Math.min(maxScroll, chipLeft - COMFORT_PAD);
        var target;
        if (lo <= hi) {
            target = Math.max(lo, Math.min(hi, center));
        } else {
            target = Math.max(0, Math.min(maxScroll, center));
        }

        if (behavior === 'auto') {
            scrollEl.scrollLeft = target;
            return;
        }
        try {
            scrollEl.scrollTo({ left: target, behavior: 'smooth' });
        } catch (_) {
            scrollEl.scrollLeft = target;
        }
    }

    /** @param {{ behavior?: 'smooth' | 'auto' }} [options] */
    function scrollFilterSegmentSelectedIntoView(options) {
        var opts = typeof options === 'object' && options !== null ? options : {};
        document.querySelectorAll('.filter-segment-scroll').forEach(function (el) {
            scrollOneSegment(el, opts);
        });
    }

    window.scrollFilterSegmentSelectedIntoView = scrollFilterSegmentSelectedIntoView;

    /** Any page with listing filters: instant jump to document top when switching filter (no smooth scroll —
     * avoids visible lag before the new section content loads). Uses the window scroll viewport only. */
    function scrollPageToTopForListingFilter() {
        var se = document.scrollingElement || document.documentElement || document.body;
        try {
            window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        } catch (_) {
            window.scrollTo(0, 0);
        }
        if (se) {
            try {
                se.scrollTop = 0;
            } catch (_) { /* ignore */ }
        }
    }
    window.scrollPageToTopForListingFilter = scrollPageToTopForListingFilter;

    function schedule() {
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                scrollFilterSegmentSelectedIntoView();
                updateFilterSegmentEvenMobile();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', schedule);
    } else {
        schedule();
    }
    (document.documentElement || document).addEventListener('turbo:load', schedule);

    var _mqEven = window.matchMedia && window.matchMedia(EVEN_MOBILE_MQ);
    if (_mqEven && _mqEven.addEventListener) {
        _mqEven.addEventListener('change', function () {
            updateFilterSegmentEvenMobile();
        });
    } else if (_mqEven && _mqEven.addListener) {
        _mqEven.addListener(updateFilterSegmentEvenMobile);
    }

    window.addEventListener(
        'resize',
        function () {
            clearTimeout(_evenMobileResizeTimer);
            _evenMobileResizeTimer = setTimeout(updateFilterSegmentEvenMobile, 100);
        },
        { passive: true }
    );
})();
