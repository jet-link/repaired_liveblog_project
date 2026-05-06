// static/js/comment_restore_ui.js
(function () {
    'use strict';

    function restoreCommentUI(root) {
        if (!root) return;

        // 🔄 re-init toggles (Show more / less)
        if (typeof window.initCommentToggles === 'function') {
            window.initCommentToggles(root);
        }

        // 🔄 re-init tooltips
        if (typeof window.initTooltips === 'function') {
            window.initTooltips(root);
        }

        // 🔄 autosize textarea if any
        root.querySelectorAll('textarea.auto-grow').forEach(ta => {
            if (typeof window.syncAutoGrowTextarea === 'function') {
                window.syncAutoGrowTextarea(ta);
            } else {
                const cs = getComputedStyle(ta);
                const minH = parseFloat(cs.minHeight) || 0;
                const noChars = !ta.value || ta.value.length === 0;
                ta.style.height = 'auto';
                const sh = ta.scrollHeight;
                let target = Math.max(minH, sh);
                if (noChars && minH > 0 && sh > minH * 1.5) {
                    target = minH;
                }
                ta.style.height = target + 'px';
            }
        });
    }
    window.restoreCommentUI = restoreCommentUI;
})();