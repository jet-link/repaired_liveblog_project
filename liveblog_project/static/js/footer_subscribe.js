/**
 * Footer "Subscribe" popover: toggle, close on outside click / Escape.
 */
(function () {
    'use strict';

    function initFooterBackToTop() {
        var btn = document.getElementById('footerBackToTop');
        if (!btn) return;
        btn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    function init() {
        initFooterBackToTop();

        var wrap = document.querySelector('.footer-subscribe-wrap');
        if (!wrap) return;

        var trigger = wrap.querySelector('.footer-subscribe-trigger');
        var popover = wrap.querySelector('.footer-subscribe-popover');
        if (!trigger || !popover) return;

        function isOpen() {
            return !popover.hasAttribute('hidden');
        }

        function openPopover() {
            popover.removeAttribute('hidden');
            trigger.setAttribute('aria-expanded', 'true');
        }

        function closePopover() {
            popover.setAttribute('hidden', '');
            trigger.setAttribute('aria-expanded', 'false');
        }

        function togglePopover() {
            if (isOpen()) {
                closePopover();
            } else {
                openPopover();
            }
        }

        trigger.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            togglePopover();
        });

        document.addEventListener(
            'click',
            function (e) {
                if (!isOpen()) return;
                if (wrap.contains(e.target)) return;
                closePopover();
            },
            false
        );

        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape' || !isOpen()) return;
            closePopover();
            trigger.focus();
        });

        popover.querySelectorAll('a[href]').forEach(function (link) {
            link.addEventListener('click', function () {
                closePopover();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
