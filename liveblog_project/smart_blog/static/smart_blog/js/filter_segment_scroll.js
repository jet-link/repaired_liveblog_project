/**
 * Horizontal segment strips (.filter-segment-scroll): scroll the selected chip
 * (.filter-reason-btn.is-selected) into a comfortable view — centered when possible,
 * with minimum padding from the scrollport edges.
 */
(function () {
    'use strict';

    /** Minimum space (px) between selected chip and inner edge of scrollport when scrolling. */
    var COMFORT_PAD = 28;

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

    function schedule() {
        requestAnimationFrame(function () {
            requestAnimationFrame(scrollFilterSegmentSelectedIntoView);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', schedule);
    } else {
        schedule();
    }
    (document.documentElement || document).addEventListener('turbo:load', schedule);
})();
